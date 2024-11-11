from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader
import cloudinary.api
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from datetime import datetime
import os
import PyPDF2
import requests  
from pydantic import BaseModel


load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskQuestionRequest(BaseModel):
    filename: str
    question: str

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    api_key=os.getenv("CLOUDINARY_API_KEY")
)


client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
collection = db[os.getenv("MONGO_COLLECTION_NAME")]




HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

def extract_text_from_pdf(file_path: str) -> str:
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = "" 
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()  
    return text

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(await file.read())
    
    text = extract_text_from_pdf(temp_file_path)

    upload_result = cloudinary.uploader.upload(temp_file_path, resource_type="auto")
    cloudinary_url = upload_result['secure_url']
    public_id = upload_result['public_id']

    document = {
        "filename": file.filename,
        "upload_date": datetime.utcnow(),
        "cloudinary_url": cloudinary_url,
        "cloudinary_public_id": public_id,
        "text": text
    }
    collection.insert_one(document)

    os.remove(temp_file_path)

    return {"message": f"File '{file.filename}' uploaded successfully to Cloudinary."}

def create_langchain_index(text: str):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

    vectorstore = FAISS.from_texts(chunks, embeddings)
    return vectorstore

def generate_text(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    response = requests.post(
        "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-2.7B",
        headers=headers,
        json={"inputs": prompt, "parameters": {"max_length": 150}}
    )

    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        raise HTTPException(status_code=500, detail="Error with Hugging Face API request.")

@app.post("/ask_question/")
async def ask_question(request: AskQuestionRequest):
    filename = request.filename
    question = request.question
    
    doc = collection.find_one({"filename": filename})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    vectorstore = create_langchain_index(doc["text"])
    qa_chain = RetrievalQA(llm=generate_text, chain_type="map_reduce")
    result = qa_chain.run(input_document=vectorstore, question=question)

    return {"question": question, "answer": result}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

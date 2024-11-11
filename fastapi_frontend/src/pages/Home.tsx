import React, { useState } from "react";

interface Message {
  text: string;
  sender: "user" | "bot";
}

export const Home: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>("Upload");

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setFileName(file.name);
      setUploadStatus("Uploading...");

      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("http://localhost:8000/upload_pdf/", {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          const data = await response.json();
          setUploadStatus("Uploaded");

          const uploadedFileName =
            data.message.match(/'(.*?)'/)?.[1] || file.name;
          setFileName(uploadedFileName);

          alert(`File uploaded successfully: ${uploadedFileName}`);
        } else {
          setUploadStatus("Upload Failed");
          alert("Failed to upload file.");
        }
      } catch (error) {
        setUploadStatus("Upload Failed");
        console.error("Error uploading file:", error);
      }
    }
  };

  const handleAskQuestion = async () => {
    if (input.trim()) {
      setMessages([...messages, { text: input, sender: "user" }]);
      setInput("");

      try {
        const response = await fetch("http://localhost:8000/ask_question/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            filename: fileName,
            question: input,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setMessages((prevMessages) => [
            ...prevMessages,
            { text: data.answer || "No answer found.", sender: "bot" },
          ]);
        } else {
          setMessages((prevMessages) => [
            ...prevMessages,
            { text: "Try again later.", sender: "bot" },
          ]);
        }
      } catch (error) {
        console.error("Error:", error);
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: "Try again later.", sender: "bot" },
        ]);
      }
    }
  };

  return (
    <div className="flex flex-col w-full h-full mx-auto bg-white shadow-lg overflow-hidden">
      <nav className="flex items-center justify-between p-4 bg-slate-200 text-white">
        <h1 className="text-lg text-slate-800 font-semibold">PDF Q&A App</h1>
        <div className="flex gap-2 items-center">
          <p className="text-slate-600">{fileName}</p>

          <label
            htmlFor="file-upload"
            className="cursor-pointer px-3 py-1 bg-slate-700 rounded-md text-white hover:bg-slate-600"
          >
            {uploadStatus}
          </label>
        </div>

        <input
          type="file"
          id="file-upload"
          className="hidden"
          onChange={handleUpload}
        />
      </nav>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`px-4 py-2 rounded-lg ${
                message.sender === "user"
                  ? "bg-slate-500 text-white"
                  : "bg-gray-200 text-gray-800"
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center p-4 border-t">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the PDF..."
          className="flex-1 border rounded-md px-4 py-2 mr-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleAskQuestion}
          className="px-4 py-2 bg-slate-500 text-white rounded-md hover:bg-slate-600"
        >
          Ask
        </button>
      </div>
    </div>
  );
};

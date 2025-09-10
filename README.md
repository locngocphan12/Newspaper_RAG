# My RAG Chat App

## 📌 Introduction  
This project is a **Retrieval-Augmented Generation (RAG) Chat Application** with the following features:  
- 🔑 User **authentication (JWT)** for signup and login.  
- 💬 Chat with the system (with RAG backend).  
- 📂 Store **chat history** in MongoDB.  
- 📜 Sidebar to display and reload previous conversations.  

👉 Goal: Build a secure and extensible chat application as a foundation for real-world AI-powered systems.  

---

## 🛠️ Tech Stack  
- **Frontend**: [Next.js](https://nextjs.org/), [React](https://react.dev/), [Tailwind CSS](https://tailwindcss.com/)  
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [MongoDB](https://www.mongodb.com/), [JWT Authentication]  
- **Languages**: TypeScript, Python  

---

## ⚡ Installation and Run

Before running the project, please make sure you have **Node.js** installed (This project used the v22 latest version).  
You can download it from [Node.js official website](https://nodejs.org/).

1. Clone the repository:

    ```bash
   git clone https://github.com/locngocphan12/Newspaper_RAG.git
    cd NewspaperRAG
    ```

2. Install python packages:

    ```bash
    pip install -r requirements.txt
    ```
   
3. Backend (FastAPI):  
    ```bash
    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8031
    ```
4. Frontend (Next.js):
    ```bash
   cd frontend
    npm install
    npm run dev
    ```
5. Access the UI:
- Open your web browser and navigate to http://localhost:3000 for RAG Demo.
## 🔑 Features
- Signup & Login
- Chat with system
- Save conversations into MongoDB
- Sidebar showing chat history
## 📜 Note

- This is only a demo version and not yet complete. Improvements will be made in the future.  
- The dataset used is not publicly released at the moment.  

- If you have any suggestions regarding the data or the project, please feel free to contact me via email: [locngocphan12@gmail.com](mailto:locngocphan12@gmail.com)

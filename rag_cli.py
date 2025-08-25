from openai import OpenAI


import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
import os

# =========================
# 1. Config
# =========================
DB_DIR = "faiss_news_db"
API_key = ""
# =========================
# 2. Load FAISS database
# =========================
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
db = FAISS.load_local(DB_DIR, embeddings, allow_dangerous_deserialization=True)

# =========================
# 3. LLM (GPT-4o-mini)
# =========================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# =========================
# 4. Prompt template
# =========================
qa_prompt = PromptTemplate(
    input_variables=["context", "input"],
    template="""
Bạn là một trợ lý thông minh. Dưới đây là ngữ cảnh từ báo chí:

{context}

Câu hỏi: {input}

Hãy trả lời ngắn gọn, chính xác dựa trên ngữ cảnh. 
Nếu không có thông tin, hãy nói: "Tôi không có thông tin trong dữ liệu."
"""
)

# =========================
# 5. Tạo retrieval chain
# =========================
combine_docs_chain = create_stuff_documents_chain(llm, qa_prompt)
retrieval_chain = create_retrieval_chain(
    db.as_retriever(search_kwargs={"k": 3}),
    combine_docs_chain
)

if __name__ == "__main__":
    print("Chatbot Hỏi Đáp Báo Chí (RAG + GPT-4o-mini)")
    print("Nhập câu hỏi, hoặc gõ 'exit' để thoát.\n")

    while True:

        query = input("Câu hỏi: ")

        if query.lower().strip() in ["exit", "quit"]:
            print("Tạm biệt!")
            break

        try:
            start = time.time()
            result = retrieval_chain.invoke({"input": query})
            end = time.time()
            print("Trả lời:", result["answer"], "\n")
            print("Nguồn: \n")
            for i, doc in enumerate(result["context"], 1):
                print(f"--- Document {i} ---")
                print("URL:", doc.metadata.get("id"))
            print('Tổng thời gian truy xuất: ',end - start)
        except Exception as e:
            print("Lỗi:", e, "\n")

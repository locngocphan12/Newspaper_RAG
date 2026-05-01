import os
import time

from fastapi import APIRouter, Depends, HTTPException
from dotenv import load_dotenv

from backend.auth_fol.auth_bearer import JWTBearer
from backend.utils import decode_jwt
from backend.database import db
from datetime import datetime
from backend.models import QueryRequest
from ..rag_cli import RAGChatbot

load_dotenv()

query_router = APIRouter()
chat_collection = db["chat_logs"]

DB_PATH = "faiss_news_db_ivf"
API_KEY = os.getenv("OPENAI_API_KEY")

# Lazy singleton – khởi tạo khi lần đầu được gọi
_chatbot: RAGChatbot | None = None


def get_chatbot() -> RAGChatbot:
    """Trả về chatbot singleton, khởi tạo nếu chưa có."""
    global _chatbot
    if _chatbot is None:
        if not API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set in environment variables.")
        _chatbot = RAGChatbot(
            db_dir=DB_PATH,
            api_key=API_KEY,
            use_reranker=True,
            use_hybrid=True,      # FAISS + BM25 + RRF
        )
    return _chatbot


# ─────────────────────────── RAG PIPELINE ────────────────────────────

def rag_pipeline(query: str) -> dict:
    """
    Chạy RAG pipeline: retrieve → rerank → generate.
    Trả về answer, sources (với similarity_score & rerank_score), used_k, processing_time.
    """
    chatbot = get_chatbot()
    start_time = time.time()
    result, used_k = chatbot.enhanced_search(query)
    processing_time = round(time.time() - start_time, 2)

    sources = []
    for i, doc in enumerate(result["context"], 1):
        sources.append({
            "doc_id": i,
            "url": doc.metadata.get("id", "N/A"),
            "section": doc.metadata.get("section", ""),
            "subsection": doc.metadata.get("subsection", ""),
            "similarity_score": doc.metadata.get("similarity_score"),
            "bm25_score": doc.metadata.get("bm25_score"),
            "rrf_score": doc.metadata.get("rrf_score"),
            "rerank_score": doc.metadata.get("rerank_score"),
            "snippet": doc.page_content[:200],
        })

    return {
        "answer": result["answer"],
        "used_k": used_k,
        "processing_time": processing_time,
        "sources": sources,
    }


# ─────────────────────────── ENDPOINT ────────────────────────────────

@query_router.post("/query")
async def query_rag(req: QueryRequest, token: str = Depends(JWTBearer())):
    """
    Endpoint RAG: nhận câu hỏi → trả lời từ dữ liệu báo chí.
    """
    payload = decode_jwt(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=403, detail="Invalid token")

    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        response = rag_pipeline(query)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")

    # Lưu log vào MongoDB
    chat_collection.insert_one({
        "user": username,
        "query": query,
        "answer": response["answer"],
        "sources": response["sources"],
        "used_k": response["used_k"],
        "processing_time": response["processing_time"],
        "timestamp": datetime.utcnow(),
    })

    return {
        "user": username,
        "query": query,
        **response,
    }

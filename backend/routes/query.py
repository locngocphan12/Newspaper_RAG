import os

from fastapi import APIRouter, Depends, HTTPException
from backend.auth_fol.auth_bearer import JWTBearer
from backend.utils import decode_jwt
from backend.database import db
from datetime import datetime
from backend.models import QueryRequest
from uuid import uuid4
from dotenv import load_dotenv
from ..rag_cli import RAGChatbot
import time

query_router = APIRouter()
chat_collection = db["chat_logs"]
DB = "faiss_news_db_ivf"
API_KEY = os.getenv("API_KEY")
chatbot = RAGChatbot(db_dir=DB, api_key=API_KEY)

# Pipeline RAG result
def rag_pipeline(query: str):
    """
    Data trả về cho RAG pipeline
    """
    start_time = time.time()
    result, used_k = chatbot.enhanced_search(query)
    end_time = time.time()
    response = {
        "answer": result["answer"],
        "used_k": used_k,
        "processing_time": round(end_time - start_time, 2),
        "sources": []
    }

    for i, doc in enumerate(result["context"], 1):
        response["sources"].append({
            "doc_id": i,
            "url": doc.metadata.get("id", "N/A"),
            "score": getattr(doc, "score", None)
        })

    return response
    # return result["answer"]

@query_router.post("/query")
def query_rag(req: QueryRequest, token: str = Depends(JWTBearer())):
    """
    Route gọi RAG
    """
    try:
        # Giải mã JWT để lấy user
        payload = decode_jwt(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=403, detail="Invalid token")
        query = req.query
        # Gọi RAG
        response = rag_pipeline(query)

        chat_collection.insert_one({
            "user": username,
            "query": query,
            "answer": response["answer"],
            "sources": response["sources"],
            "used_k": response["used_k"],
            "processing_time": response["processing_time"],
            "timestamp": datetime.utcnow()
        })

        return {
            "user": username,
            "query": query,
            **response
        }
        # # Lưu log vào MongoDB
        # chat_collection.insert_one({
        #     "user": username,
        #     "query": query,
        #     "answer": answer,
        #     "timestamp": datetime.utcnow()
        # })
        #
        # return {"user": username, "query": query, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

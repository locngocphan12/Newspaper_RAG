from fastapi import APIRouter, Depends, HTTPException
from backend.auth_fol.auth_bearer import JWTBearer
from backend.utils import decode_jwt
from backend.database import db
from datetime import datetime

query_router = APIRouter()
chat_collection = db["chat_logs"]

# Fake pipeline RAG (bạn thay sau)
def rag_pipeline(query: str):
    return f"Fake RAG answer for: {query}"

@query_router.post("/query")
def query_rag(query: str, token: str = Depends(JWTBearer())):
    """
    Route gọi RAG (tạm fake).
    User lấy từ JWT token thay vì param.
    """
    try:
        # Giải mã JWT để lấy user
        payload = decode_jwt(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=403, detail="Invalid token")

        # Gọi RAG
        answer = rag_pipeline(query)

        # Lưu log vào MongoDB
        chat_collection.insert_one({
            "user": username,
            "query": query,
            "answer": answer,
            "timestamp": datetime.utcnow()
        })

        return {"user": username, "query": query, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

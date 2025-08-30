from fastapi import APIRouter, Depends
from backend.auth_fol.auth_bearer import JWTBearer
from backend.utils import decode_jwt
from backend.database import db

history_router = APIRouter()
chat_collection = db["chat_logs"]

@history_router.get("/history")
def get_history(token: str = Depends(JWTBearer())):
    """
    Lấy lịch sử chat của user (từ MongoDB).
    """
    payload = decode_jwt(token)
    username = payload.get("sub")
    logs = chat_collection.find({"user": username}).sort("timestamp", -1)
    history = []
    for log in logs:
        history.append({
            "query": log["query"],
            "answer": log["answer"],
            "timestamp": log["timestamp"]
        })
    return {"history": history}

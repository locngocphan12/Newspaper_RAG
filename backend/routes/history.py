from fastapi import APIRouter, Depends, Query
from backend.auth_fol.auth_bearer import JWTBearer
from backend.utils import decode_jwt
from backend.database import db

history_router = APIRouter()
chat_collection = db["chat_logs"]


@history_router.get("/history")
async def get_history(
    token: str = Depends(JWTBearer()),
    limit: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi trả về"),
    skip: int = Query(default=0, ge=0, description="Bỏ qua N bản ghi đầu"),
):
    """
    Lấy lịch sử chat của user từ MongoDB.
    Hỗ trợ phân trang qua limit & skip.
    """
    payload = decode_jwt(token)
    username = payload.get("sub")

    cursor = (
        chat_collection
        .find({"user": username})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )

    history = []
    for log in cursor:
        history.append({
            "query": log.get("query"),
            "answer": log.get("answer"),
            "sources": log.get("sources", []),
            "used_k": log.get("used_k"),
            "processing_time": log.get("processing_time"),
            "timestamp": log.get("timestamp"),
        })

    return {"total_returned": len(history), "history": history}

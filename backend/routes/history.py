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
    return history

# @history_router.get("/history")
# def get_history(token: str = Depends(JWTBearer())):
#     payload = decode_jwt(token)
#     username = payload.get("sub")
#
#     pipeline = [
#         {"$match": {"user": username}},
#         {"$sort": {"timestamp": -1}},
#         {"$group": {
#             "_id": "$conversation_id",
#             "last_query": {"$first": "$query"},
#             "last_answer": {"$first": "$answer"},
#             "last_time": {"$first": "$timestamp"}
#         }},
#         {"$sort": {"last_time": -1}}
#     ]
#
#     conversations = list(chat_collection.aggregate(pipeline))
#     return conversations
#
# @history_router.get("/history/{conversation_id}")
# def get_conversation(conversation_id: str, token: str = Depends(JWTBearer())):
#     payload = decode_jwt(token)
#     username = payload.get("sub")
#
#     logs = chat_collection.find({"user": username, "conversation_id": conversation_id}).sort("timestamp", 1)
#     return [
#         {"role": "user", "content": log["query"]} if log.get("query") else
#         {"role": "assistant", "content": log["answer"]}
#         for log in logs
#     ]





from fastapi import FastAPI
from backend.auth import auth_router
from backend.routes.query import query_router
from backend.routes.history import history_router

app = FastAPI(title="Newspaper RAG API")

# Đăng ký các router
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(query_router, tags=["query"])
app.include_router(history_router, tags=["history"])

@app.get("/")
def root():
    return {"msg": "🚀 RAG API running..."}

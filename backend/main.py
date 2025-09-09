from fastapi import FastAPI
from backend.auth import auth_router
from backend.routes.query import query_router
from backend.routes.history import history_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Newspaper RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # hoặc chỉ định ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Đăng ký các router
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(query_router, tags=["query"])
app.include_router(history_router, tags=["history"])

@app.get("/")
def root():
    return {"msg": "🚀 RAG API running..."}

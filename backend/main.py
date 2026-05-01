import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.auth import auth_router
from backend.routes.query import query_router
from backend.routes.history import history_router

load_dotenv()

# ─────────────────────── LIFESPAN (startup/shutdown) ─────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm-up: khởi tạo chatbot singleton khi server start."""
    from backend.routes.query import get_chatbot
    try:
        get_chatbot()
        print("✅ RAG Chatbot warmed up successfully.")
    except Exception as e:
        print(f"⚠️ Chatbot warm-up failed (will retry on first request): {e}")
    yield
    # shutdown logic có thể thêm ở đây


# ─────────────────────────── APP ─────────────────────────────────────────────

app = FastAPI(title="Newspaper RAG API", version="2.0.0", lifespan=lifespan)

# CORS – đọc từ env hoặc dùng mặc định
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(query_router, tags=["query"])
app.include_router(history_router, tags=["history"])


@app.get("/")
def root():
    return {"msg": "🤖 RAG API running...", "version": "2.0.0"}


@app.get("/health")
def health():
    """Health-check endpoint."""
    return {"status": "ok"}

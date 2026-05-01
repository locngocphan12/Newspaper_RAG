# 📰 Newspaper RAG – Vietnamese News Q&A System

> **RAG** (Retrieval-Augmented Generation) · **Hybrid Search (FAISS + BM25 + RRF)** · **Cross-Encoder Reranking** · **JWT Auth** · **MongoDB** · **Next.js**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14%2B-black)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Overview

A full-stack news Q&A chatbot that answers questions about Vietnamese newspaper articles using a multi-stage RAG pipeline with hybrid search.

| Feature | Description |
|---|---|
| 🔑 JWT Authentication | Secure signup / login with bcrypt-hashed passwords |
| 💬 RAG Chat | Question answering grounded in real news data |
| 🔀 Hybrid Search | FAISS dense search + BM25 sparse search fused via RRF |
| 🔄 Cross-Encoder Reranking | Re-scores retrieved candidates for higher precision |
| 📂 Chat History | Persisted conversation history with pagination |
| 🗄️ MongoDB | Stores user accounts and chat logs |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js)                    │
│         /login  /signup  /chat  /history                │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP/REST  (JWT Bearer)
┌───────────────────▼─────────────────────────────────────┐
│                  BACKEND (FastAPI)                       │
│                                                         │
│  POST /auth/signup   POST /auth/login                   │
│  POST /query         GET  /history                      │
│  GET  /health                                           │
│                                                         │
│  ┌──────────────── RAG Pipeline ──────────────────┐     │
│  │                                                │     │
│  │  Query ──► Bi-Encoder Embed (MiniLM, 384-dim) │     │
│  │                    │                           │     │
│  │         ┌──────────┴──────────┐               │     │
│  │         │                     │               │     │
│  │   FAISS IVF Search        BM25 Search         │     │
│  │   (dense / semantic)    (sparse / keyword)    │     │
│  │         │                     │               │     │
│  │         └──────────┬──────────┘               │     │
│  │                    │                           │     │
│  │       Reciprocal Rank Fusion (RRF)             │     │
│  │       Merge & deduplicate results              │     │
│  │                    │                           │     │
│  │       Cross-Encoder Reranker                   │     │
│  │       (mmarco-mMiniLMv2-L12-H384-v1)          │     │
│  │       Re-score → top-k docs                   │     │
│  │                    │                           │     │
│  │       GPT-4o-mini (OpenAI API)                │     │
│  │       Generate answer from context             │     │
│  │                                                │     │
│  └────────────────────────────────────────────────┘     │
│                                                         │
│  MongoDB ◄── save log (query, answer, sources, time)   │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
NewspaperRAG/
├── backend/
│   ├── main.py              # FastAPI app, CORS, lifespan warm-up
│   ├── auth.py              # Signup / Login route handlers
│   ├── database.py          # MongoDB connection
│   ├── models.py            # Pydantic schemas
│   ├── utils.py             # JWT helpers, bcrypt
│   ├── rag_cli.py           # ⭐ Core RAG: embed → hybrid search → rerank → generate
│   ├── auth_fol/
│   │   └── auth_bearer.py   # JWT Bearer middleware
│   └── routes/
│       ├── query.py         # POST /query  (RAG endpoint)
│       └── history.py       # GET  /history (paginated)
│
├── data/                    # Vietnamese news data (JSON)
│   ├── DanTri/              # 8 topics (social, real estate, education…)
│   ├── LaoDong/             # 2 topics
│   └── ThanhNien/           # 4 topics
│
├── faiss_news_db_ivf/       # Pre-built FAISS IVF index
│   ├── index.faiss          # ~359,959 vectors
│   ├── index.pkl
│   └── metadata.json
│
├── frontend/                # Next.js + Tailwind CSS
│   ├── app/
│   │   ├── chat/            # Main chat UI
│   │   ├── login/           # Auth pages
│   │   ├── signup/
│   │   └── history/         # Chat history page
│   └── lib/
│       ├── auth.ts          # Token management
│       └── app.ts           # API calls
│
├── build_index_with_ivf.py  # Script to build FAISS IVF index from scratch
├── build_index_with_flat.py # Script to build FAISS Flat index
├── test_system.py           # ⭐ End-to-end system verification
├── requirements.txt
└── .env                     # Environment variables (never commit this)
```

---

## 🔄 RAG Pipeline – Detailed Flow

### Stage 1 – Index Building (run once, already done)

```
data/*.json
  → load_all_documents()            # read 14 JSON files → Document objects
  → RecursiveCharacterTextSplitter  # chunk_size=500, overlap=60
  → HuggingFaceEmbeddings           # paraphrase-multilingual-MiniLM-L12-v2 (dim=384)
  → FAISS IndexIVFFlat              # nlist=100, nprobe=10, L2 metric
  → saved to faiss_news_db_ivf/     # ~359,959 vectors
```

### Stage 2 – Query Handling (every request)

```
User query: "How are housing prices in Hanoi changing?"
    │
    ▼ [1] parse_search_params()  →  clean_query, k=3
    │
    ▼ [2] Hybrid Search
    │
    │   ┌────────────────────────────────────────┐
    │   │  FAISS Dense Search  (k×4 = 12 docs)  │
    │   │  embed query → 384D vector              │
    │   │  IVF index ANN search (L2 distance)    │
    │   │  similarity_score = 1/(1+distance)     │
    │   └──────────────┬─────────────────────────┘
    │                  │
    │   ┌──────────────┴─────────────────────────┐
    │   │  BM25 Sparse Search  (k×4 = 12 docs)  │
    │   │  tokenize query → TF-IDF scoring       │
    │   │  normalized_bm25_score ∈ [0, 1]        │
    │   └──────────────┬─────────────────────────┘
    │                  │
    ▼ [3] RRF Fusion
    │   RRF_score(doc) = 1/(60 + rank_FAISS) + 1/(60 + rank_BM25)
    │   Merge + deduplicate → ranked candidate list
    │
    ▼ [4] Cross-Encoder Rerank  (top candidates → top-3)
    │   predict([(query, doc)] × N) → rerank_score
    │   keep top-k by rerank_score
    │
    ▼ [5] GPT-4o-mini generates answer from top-3 context docs  (~1–3s)
    │
    ▼ [6] Return: answer + sources (url, scores, snippet)
    │
    ▼ [7] Save chat log to MongoDB
```

### Why Two-Stage Retrieval?

| | Bi-Encoder (FAISS) | Cross-Encoder |
|---|---|---|
| How it works | Embeds query & doc **independently** | Reads query **and** doc together via attention |
| Speed | ~12 ms for 360k vectors | ~177 ms for 12 docs (CPU) |
| Accuracy | Good (semantic similarity) | Higher (deeper query-doc interaction) |
| Role | Fast candidate retrieval | Precise final ranking |

### Why Hybrid Search?

| Scenario | FAISS only | BM25 only | Hybrid |
|---|---|---|---|
| Query "capital city" → doc has "Hanoi" | ✅ | ❌ | ✅ |
| Exact keyword match (e.g. "COVID-19") | ⚠️ | ✅ | ✅ |
| Named entities / brand names | ⚠️ | ✅ | ✅ |
| Conceptual / paraphrase queries | ✅ | ❌ | ✅ |

---

## ⚡ Setup & Installation

### System Requirements

| Component | Minimum | Notes |
|---|---|---|
| Python | 3.11+ | Tested on 3.13 |
| Node.js | 18 LTS+ | v22 recommended |
| MongoDB | 6.0+ | Running locally |
| RAM | 8 GB | 16 GB recommended |
| GPU | ❌ Not required | Fully CPU-based |
| Disk | ~3 GB | Model cache + FAISS index |

---

### Step 0 – Clone the Repository

```bash
git clone https://github.com/locngocphan12/Newspaper_RAG.git
cd NewspaperRAG/NewspaperRAG
```

---

### Step 1 – Create the `.env` File

Create a `.env` file inside `NewspaperRAG/NewspaperRAG/` (same level as `backend/`):

```dotenv
MONGO_URI=mongodb://localhost:27017
JWT_SECRET=your_secret_key_replace_this
JWT_ALGORITHM=HS256
OPENAI_API_KEY=sk-proj-...your_key...
ALLOWED_ORIGINS=http://localhost:3000
```

> ⚠️ **Never commit `.env` to Git.** Add it to `.gitignore`.

---

### Step 2 – Start MongoDB

```bash
# Windows – if MongoDB Community is installed
mongod --dbpath C:\data\db

# Or if installed as a service:
net start MongoDB

# Verify MongoDB is running:
mongosh --eval "db.adminCommand('ping')"
```

---

### Step 3 – Create Python Virtual Environment

```bash
# From NewspaperRAG/NewspaperRAG
python -m venv rag_env

# Activate (Windows PowerShell)
.\rag_env\Scripts\Activate.ps1

# Or CMD
rag_env\Scripts\activate.bat

# Install dependencies (~5–15 minutes on first run – PyTorch is large)
pip install -r requirements.txt
```

---

### Step 4 – (Optional) Rebuild the FAISS Index

> **Skip this step** if `faiss_news_db_ivf/` already exists with 3 files.

```bash
# Always run from NewspaperRAG/NewspaperRAG
python build_index_with_ivf.py
```

Process: load JSON → split chunks → embed (5–20 min) → build IVF → save.

---

### Step 5 – Verify the System ✅

> ⚠️ **Activate the venv first**, or call the venv Python directly:

```powershell
# Option 1 – activate venv then run
.\rag_env\Scripts\Activate.ps1
python test_system.py

# Option 2 – call venv Python directly (no activation needed)
.\rag_env\Scripts\python.exe test_system.py
```

Expected output (first run will download models):

```
✅ OPENAI_API_KEY: set (sk-proj-...)
✅ MONGO_URI: mongodb://localhost:27017
✅ JWT_SECRET: set
✅ Embedding model loaded in ~30s   ← first run; ~3s after caching
✅ Embedding dim: 384
✅ FAISS loaded in ~3s | ntotal=359959
✅ Similarity search (12ms) → 6 docs
✅ Reranker loaded in ~21s           ← first run; ~5s after caching
✅ Reranked 6 docs in ~177ms (CPU)
✅ MongoDB connected
✅ FastAPI app imported OK
     Routes: ['/auth/signup', '/auth/login', '/query', '/history', '/', '/health']
```

---

### Step 6 – Run the Backend

> ⚠️ **Activate the venv** or use `.\rag_env\Scripts\uvicorn.exe` directly.

```powershell
# Option 1 – use venv uvicorn directly (no activation needed)
.\rag_env\Scripts\uvicorn.exe backend.main:app --reload --host 127.0.0.1 --port 8031

# Option 2 – activate venv then run
.\rag_env\Scripts\Activate.ps1
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8031
```

Successful startup output:
```
INFO:     Uvicorn running on http://127.0.0.1:8031
✅ RAG Chatbot warmed up successfully.
INFO:     Application startup complete.
```

- **Swagger UI**: http://127.0.0.1:8031/docs
- **Health check**: http://127.0.0.1:8031/health

> ⏳ **First startup** takes ~50–90s to load AI models and build the BM25 index.  
> **Subsequent starts** are faster (~10s) as models are cached.

---

### Step 7 – Run the Frontend

Open a **new terminal** (keep the backend terminal running):

```bash
cd frontend
npm install        # ~2 minutes on first run
npm run dev
```

Open **http://localhost:3000** in your browser.

---

### Startup Order Summary

```
1. mongod              ← MongoDB
2. uvicorn backend...  ← FastAPI backend  (port 8031)
3. npm run dev         ← Next.js frontend (port 3000)
```

---

## 🔌 API Reference

### `POST /auth/signup`
```json
// Request
{ "username": "alice", "password": "Pass@1234", "confirm_password": "Pass@1234" }

// Response 200
{ "msg": "User created successfully" }
```

**Password rules**: ≥8 characters, must include letters, digits, and a special character.

---

### `POST /auth/login`
```json
// Request
{ "username": "alice", "password": "Pass@1234" }

// Response 200
{ "access_token": "eyJhbGci...", "token_type": "bearer" }
```

---

### `POST /query` *(requires JWT)*
```
Header: Authorization: Bearer <token>
```
```json
// Request
{ "query": "How are housing prices in Hanoi changing?" }

// Response 200
{
  "user": "alice",
  "query": "How are housing prices in Hanoi changing?",
  "answer": "According to news data, land prices in suburban Hanoi...",
  "used_k": 3,
  "processing_time": 2.41,
  "sources": [
    {
      "doc_id": 1,
      "url": "https://dantri.com.vn/bat-dong-san/...",
      "section": "bat-dong-san",
      "similarity_score": 0.1012,
      "bm25_score": 0.8750,
      "rrf_score": 0.031746,
      "rerank_score": 3.927,
      "snippet": "Land prices in suburban areas..."
    }
  ]
}
```

---

### `GET /history?limit=20&skip=0` *(requires JWT)*
```json
{
  "total_returned": 5,
  "history": [
    {
      "query": "...", "answer": "...",
      "sources": [...],
      "used_k": 3, "processing_time": 2.4,
      "timestamp": "2026-05-01T10:30:00"
    }
  ]
}
```

---

## 💬 Query Syntax Reference

| Pattern | Example | k |
|---|---|---|
| `top N ...` | `top 5 AI news` | 5 |
| `N articles about ...` | `3 articles about inflation` | 3 |
| `find N ...` | `find 4 articles about EVs` | 4 |
| `... in detail` | `detailed info about labor market` | 5 |
| `... summary` | `quick summary of real estate` | 2 |
| *(default)* | `AI in education` | 3 |

### Tips for Best Results

```
✅ Specific + multi-keyword:  "housing prices Hanoi increase 2025"
✅ Natural language:          "Why did gas prices rise at year end?"
✅ Mix concepts + exact terms: "domestic tourism recovery post-pandemic visitors"

❌ Too short / vague:         "economy"
❌ Yes/No questions:          "did it increase?"
```

---

## 🧠 AI Models

| Model | Type | Size | Used For |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | Bi-Encoder | ~471 MB | Query & document embedding |
| `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | Cross-Encoder | ~471 MB | Multilingual reranking |
| `gpt-4o-mini` | LLM (OpenAI API) | – | Answer generation |

> **Total RAM at runtime**: ~1.5–2 GB (models) + ~600 MB (FAISS index)

---

## 📊 Performance Benchmarks (CPU, no GPU)

| Operation | Latency |
|---|---|
| Load embedding model (first run) | ~28 s |
| Load FAISS DB (359k vectors) | ~3 s |
| Build BM25 index (359k docs, once at startup) | ~30–60 s |
| Load reranker (first run) | ~21 s |
| FAISS IVF search (k=12) | ~12 ms |
| BM25 search (k=12) | ~50 ms |
| RRF fusion | < 5 ms |
| Cross-Encoder rerank (12 docs) | ~177 ms |
| GPT-4o-mini API call | ~1–3 s |
| **Total latency per query (after warm-up)** | **~2–4 s** |

---

## 🐛 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `No module named 'langchain_community'` | Using system Python instead of venv | Run: `.\rag_env\Scripts\python.exe test_system.py` |
| `MutableMapping` ImportError | Old pymongo + Python 3.13 (system) | Use venv: `.\rag_env\Scripts\Activate.ps1` |
| `FileNotFoundError: faiss_news_db_ivf` | Wrong working directory | `cd NewspaperRAG/NewspaperRAG` before running uvicorn |
| `OPENAI_API_KEY is not set` | `.env` in wrong location | `.env` must be at `NewspaperRAG/NewspaperRAG/.env` |
| `No module named 'rank_bm25'` | Missing dependency | `pip install rank-bm25` |
| MongoDB connection failed | MongoDB not running | `mongod --dbpath C:\data\db` |
| Slow startup (~50–90 s) | Models not cached yet | Normal on first run; faster after caching |
| `ModuleNotFoundError` | venv not activated | `.\rag_env\Scripts\Activate.ps1` |
| Port 8031 already in use | Old server still running | `netstat -ano \| findstr 8031` → kill process |

---

## 🔮 Roadmap

- [x] **BM25 Hybrid Search** – sparse (keyword) + dense (semantic) + RRF fusion
- [ ] **Query Rewriting / HyDE** – LLM rewrites query before embedding
- [ ] **Streaming Response** – stream GPT tokens to frontend in real-time
- [ ] **Conversation Memory** – multi-turn chat with context window
- [ ] **Better Vietnamese Embedding** – `bkai-foundation-models/vietnamese-bi-encoder`
- [ ] **Docker Compose** – containerize the entire stack

---

## 👤 Author

**Phan Lộc Ngọc** – locngocphan12@gmail.com

---

## 📄 License

[MIT License](LICENSE)

"""
System test script - chay tren CPU, khong can GPU.
Usage:
  Windows PowerShell : .\\rag_env\\Scripts\\python.exe test_system.py
  Windows CMD        : rag_env\\Scripts\\python.exe test_system.py
  Sau khi kich hoat  : python test_system.py
"""
import os
import sys
import time

# ── Kiểm tra Python đang dùng có phải venv không ──────────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
_venv_python_win = os.path.join(_script_dir, "rag_env", "Scripts", "python.exe")
_venv_python_unix = os.path.join(_script_dir, "rag_env", "bin", "python")
_using_venv = (
    sys.executable == _venv_python_win
    or sys.executable == _venv_python_unix
    or "rag_env" in sys.executable
)

if not _using_venv:
    print("=" * 55)
    print("  CANH BAO: Ban dang dung Python he thong!")
    print(f"  Python hien tai: {sys.executable}")
    print()
    print("  Hay chay lai bang Python trong venv:")
    print()
    print("  Windows PowerShell:")
    print(r"    .\rag_env\Scripts\python.exe test_system.py")
    print()
    print("  Windows CMD:")
    print(r"    rag_env\Scripts\python.exe test_system.py")
    print()
    print("  Hoac kich hoat venv truoc:")
    print(r"    .\rag_env\Scripts\Activate.ps1")
    print(r"    python test_system.py")
    print("=" * 55)
    sys.exit(1)

os.chdir(_script_dir)

from dotenv import load_dotenv
load_dotenv()

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def separator(title=""):
    print(f"\n{'='*55}")
    if title:
        print(f"  {title}")
        print(f"{'='*55}")


# ─────────────────────────────────────────────────────────
separator("Test 1: Environment Variables")
# ─────────────────────────────────────────────────────────
api_key = os.getenv("OPENAI_API_KEY", "")
mongo_uri = os.getenv("MONGO_URI", "")
jwt_secret = os.getenv("JWT_SECRET", "")

print(f"{PASS if api_key else FAIL} OPENAI_API_KEY: {'set (' + api_key[:12] + '...)' if api_key else 'MISSING'}")
print(f"{PASS if mongo_uri else FAIL} MONGO_URI: {mongo_uri or 'MISSING'}")
print(f"{PASS if jwt_secret else FAIL} JWT_SECRET: {'set' if jwt_secret else 'MISSING'}")

# ─────────────────────────────────────────────────────────
separator("Test 2: Load Embedding Model (CPU)")
# ─────────────────────────────────────────────────────────
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    t0 = time.time()
    emb = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    elapsed = time.time() - t0
    test_vec = emb.embed_query("kinh tế Việt Nam")
    print(f"{PASS} Embedding model loaded in {elapsed:.1f}s")
    print(f"{PASS} Embedding dim: {len(test_vec)}")
except Exception as e:
    print(f"{FAIL} Embedding model error: {e}")
    emb = None

# ─────────────────────────────────────────────────────────
separator("Test 3: Load FAISS Database")
# ─────────────────────────────────────────────────────────
db = None
if emb:
    try:
        from langchain_community.vectorstores import FAISS
        db_path = "faiss_news_db_ivf"
        t0 = time.time()
        db = FAISS.load_local(db_path, emb, allow_dangerous_deserialization=True)
        elapsed = time.time() - t0
        print(f"{PASS} FAISS loaded in {elapsed:.1f}s | ntotal={db.index.ntotal}")

        # Quick search
        t0 = time.time()
        results = db.similarity_search_with_score("giá nhà đất tăng", k=6)
        s_time = time.time() - t0
        print(f"{PASS} Similarity search ({s_time*1000:.0f}ms) → {len(results)} docs")
        for doc, dist in results[:2]:
            sim = round(1 / (1 + dist), 4)
            print(f"       sim={sim} | {doc.metadata.get('id','?')[:60]}")
    except Exception as e:
        print(f"{FAIL} FAISS error: {e}")

# ─────────────────────────────────────────────────────────
separator("Test 4: Cross-Encoder Reranker (CPU)")
# ─────────────────────────────────────────────────────────
reranker = None
if db:
    try:
        from sentence_transformers import CrossEncoder
        import numpy as np

        RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        print(f"Loading: {RERANKER_MODEL} ...")
        t0 = time.time()
        reranker = CrossEncoder(RERANKER_MODEL)
        elapsed = time.time() - t0
        print(f"{PASS} Reranker loaded in {elapsed:.1f}s")

        # Test reranking
        query = "giá nhà đất tăng"
        docs = [doc for doc, _ in results]
        pairs = [(query, doc.page_content) for doc in docs]

        t0 = time.time()
        scores = reranker.predict(pairs)
        scores = np.atleast_1d(scores).tolist()
        r_time = time.time() - t0

        print(f"{PASS} Reranked {len(docs)} docs in {r_time*1000:.0f}ms (CPU)")
        sorted_pairs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        for i, (sc, doc) in enumerate(sorted_pairs[:2], 1):
            print(f"       #{i} rerank={sc:.3f} | {doc.metadata.get('id','?')[:55]}")
    except Exception as e:
        print(f"{WARN} Reranker: {e}")
        print(f"{WARN} Reranking will be disabled (fallback to similarity only)")

# ─────────────────────────────────────────────────────────
separator("Test 5: MongoDB Connection")
# ─────────────────────────────────────────────────────────
try:
    from pymongo import MongoClient
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    client.server_info()
    print(f"{PASS} MongoDB connected: {mongo_uri}")
    client.close()
except Exception as e:
    print(f"{FAIL} MongoDB: {e}")
    print(f"     → Hãy chắc chắn MongoDB đang chạy: mongod --dbpath <path>")

# ─────────────────────────────────────────────────────────
separator("Test 6: FastAPI App Import")
# ─────────────────────────────────────────────────────────
try:
    import sys
    sys.path.insert(0, os.getcwd())
    # chỉ import app, không start server
    from backend.main import app
    routes = [r.path for r in app.routes]
    print(f"{PASS} FastAPI app imported OK")
    print(f"     Routes: {[r for r in routes if not r.startswith('/openapi')]}")
except Exception as e:
    print(f"{FAIL} FastAPI import error: {e}")

# ─────────────────────────────────────────────────────────
separator("Summary")
# ─────────────────────────────────────────────────────────
print("Nếu tất cả PASS → chạy server:")
print("  uvicorn backend.main:app --reload --host 127.0.0.1 --port 8031")
print("  cd frontend && npm run dev")
print()


import argparse
import os
import re
import time
from typing import Tuple, Dict, Any, List, Optional

import warnings
import numpy as np

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi


class RAGChatbot:
    def __init__(
        self,
        db_dir: str = "faiss_news_db_ivf",
        api_key: str = "",
        use_reranker: bool = True,
        reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.5,
    ):
        """
        Args:
            db_dir (str): Đường dẫn đến thư mục FAISS database
            api_key (str): OpenAI API key
            use_reranker (bool): Có dùng cross-encoder reranker không
            reranker_model (str): Tên model cross-encoder
            use_hybrid (bool): Có dùng hybrid search (FAISS + BM25) không
            hybrid_alpha (float): Trọng số cho FAISS score (0.0=BM25 only, 1.0=FAISS only)
        """
        self.db_dir = db_dir
        self.api_key = api_key
        self.default_k = 3
        self.use_reranker = use_reranker
        self.use_hybrid = use_hybrid
        self.hybrid_alpha = hybrid_alpha  # weight for FAISS in RRF weighted mode
        # Retrieve nhiều hơn k để reranker có nhiều ứng viên
        self.retrieval_multiplier = 4

        # Initialize components
        self._init_embeddings()
        self._load_database()
        self._init_llm()
        self._init_prompt()
        self._create_chains()
        if use_reranker:
            self._init_reranker(reranker_model)
        if use_hybrid:
            self._init_bm25()

        print(f"✅ RAG Chatbot initialized with database: {db_dir}")
        print(f"✅ Reranker: {'enabled (' + reranker_model + ')' if use_reranker else 'disabled'}")
        print(f"✅ Hybrid Search: {'enabled (alpha=' + str(hybrid_alpha) + ')' if use_hybrid else 'disabled'}")

    def _init_embeddings(self):
        """Khởi tạo embedding model"""
        print("⏳ Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print("✅ Embedding model loaded")

    def _load_database(self):
        """Load FAISS database"""
        if not os.path.exists(self.db_dir):
            raise FileNotFoundError(f"Database directory not found: {self.db_dir}")

        print(f"⏳ Loading FAISS database from: {self.db_dir}")
        try:
            self.db = FAISS.load_local(
                self.db_dir,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"✅ FAISS database loaded successfully")
            print(f"📊 Total vectors in database: {self.db.index.ntotal}")
        except Exception as e:
            raise Exception(f"Error loading database: {str(e)}")

    def _init_llm(self):
        """Khởi tạo LLM"""
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        print("⏳ Initializing LLM...")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=self.api_key
        )
        print("✅ LLM initialized")

    def _init_prompt(self):
        """Khởi tạo prompt template"""
        self.qa_prompt = PromptTemplate(
            input_variables=["context", "input"],
            template="""Bạn là một trợ lý thông minh về tin tức. Dưới đây là ngữ cảnh từ báo chí:

{context}

Câu hỏi: {input}

Hãy trả lời ngắn gọn, chính xác dựa trên ngữ cảnh. 
Nếu không có thông tin, hãy nói: "Tôi không có thông tin trong dữ liệu."
"""
        )

    def _create_chains(self):
        """Tạo combine_docs_chain"""
        self.combine_docs_chain = create_stuff_documents_chain(self.llm, self.qa_prompt)

    def _init_reranker(self, model_name: str):
        """Khởi tạo Cross-Encoder reranker"""
        print(f"⏳ Loading reranker model: {model_name}...")
        try:
            self.reranker = CrossEncoder(model_name)
            print("✅ Reranker loaded")
        except Exception as e:
            print(f"⚠️ Failed to load reranker: {e}. Reranking disabled.")
            self.reranker = None
            self.use_reranker = False

    def _init_bm25(self):
        """Build BM25 index từ toàn bộ documents trong FAISS docstore"""
        print("⏳ Building BM25 index from FAISS docstore...")
        print("   ⚠️  Có thể mất 30-60 giây với large database...")

        # Lấy tất cả documents từ FAISS docstore
        self.bm25_docs: List[Document] = list(self.db.docstore._dict.values())
        self.bm25_doc_ids: List[str] = list(self.db.docstore._dict.keys())

        # Tokenize: simple whitespace split (phù hợp tiếng Việt cơ bản)
        tokenized_corpus = [doc.page_content.lower().split() for doc in self.bm25_docs]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Tạo lookup dict: content_hash → index trong bm25_docs
        self._content_to_bm25_idx = {
            doc.page_content: i for i, doc in enumerate(self.bm25_docs)
        }

        print(f"✅ BM25 index built with {len(self.bm25_docs)} documents")

    # ─────────────────────────── HYBRID SEARCH ────────────────────────────

    def _bm25_search(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """
        BM25 keyword search.

        Returns:
            List of (document, normalized_bm25_score)
        """
        tokenized_query = query.lower().split()
        raw_scores = self.bm25.get_scores(tokenized_query)

        # Lấy top-k indices
        top_indices = np.argsort(raw_scores)[::-1][:k]

        # Normalize scores về [0, 1]
        max_score = float(raw_scores[top_indices[0]]) if len(top_indices) > 0 else 1.0
        if max_score == 0:
            max_score = 1.0

        results = []
        for idx in top_indices:
            normalized = float(raw_scores[idx]) / max_score
            results.append((self.bm25_docs[idx], normalized))

        return results

    def _reciprocal_rank_fusion(
        self,
        faiss_results: List[Tuple[Document, float]],
        bm25_results: List[Tuple[Document, float]],
        rrf_k: int = 60,
    ) -> List[Tuple[Document, float]]:
        """
        Reciprocal Rank Fusion để ghép kết quả từ FAISS và BM25.

        Công thức RRF:
            RRF_score(doc) = Σ  1 / (rrf_k + rank_i)
            với rank_i là vị trí của doc trong bảng xếp hạng thứ i

        Args:
            faiss_results: Danh sách (doc, faiss_score), đã sort tốt nhất → tệ nhất
            bm25_results:  Danh sách (doc, bm25_score), đã sort tốt nhất → tệ nhất
            rrf_k: Hằng số RRF (default=60, cứng nhất trong literature)

        Returns:
            Danh sách (doc, rrf_score) đã sort giảm dần theo rrf_score
        """
        # Key: page_content (unique identifier)
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        # ── FAISS contribution ──
        for rank, (doc, _) in enumerate(faiss_results):
            key = doc.page_content
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)

        # ── BM25 contribution ──
        for rank, (doc, _) in enumerate(bm25_results):
            key = doc.page_content
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)

        # Sort giảm dần theo RRF score
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [(doc_map[key], score) for key, score in sorted_items]

    def hybrid_retrieve_and_rerank(
        self,
        query: str,
        k: int,
    ) -> List[Document]:
        """
        Hybrid search: FAISS + BM25 → RRF → Cross-Encoder Rerank → top-k

        Pipeline:
            1. FAISS dense search       → retrieve_k documents
            2. BM25 sparse search       → retrieve_k documents
            3. RRF fusion               → merged & deduplicated list
            4. Cross-Encoder rerank     → top-k documents

        Args:
            query: Câu truy vấn sạch
            k: Số document cần trả về

        Returns:
            Danh sách document với metadata: similarity_score, bm25_score, rrf_score, rerank_score
        """
        retrieve_k = min(k * self.retrieval_multiplier, self.db.index.ntotal)
        retrieve_k = max(retrieve_k, k)

        # ── Bước 1: FAISS Dense Search ──────────────────────────────────
        faiss_raw = self.db.similarity_search_with_score(query, k=retrieve_k)
        faiss_results: List[Tuple[Document, float]] = []
        for doc, distance in faiss_raw:
            doc.metadata["similarity_score"] = round(float(1 / (1 + distance)), 4)
            doc.metadata["faiss_distance"] = round(float(distance), 4)
            faiss_results.append((doc, doc.metadata["similarity_score"]))

        # ── Bước 2: BM25 Sparse Search ───────────────────────────────────
        bm25_raw = self._bm25_search(query, k=retrieve_k)
        for doc, score in bm25_raw:
            doc.metadata["bm25_score"] = round(score, 4)

        # ── Bước 3: RRF Fusion ───────────────────────────────────────────
        fused = self._reciprocal_rank_fusion(faiss_results, bm25_raw)
        for doc, rrf_score in fused:
            doc.metadata["rrf_score"] = round(rrf_score, 6)

        # Lấy candidates để rerank (nhiều hơn k một chút)
        candidates = [doc for doc, _ in fused[: max(retrieve_k, k * 2)]]

        # ── Bước 4: Cross-Encoder Rerank ────────────────────────────────
        if self.use_reranker and self.reranker and len(candidates) > 1:
            final_docs = self.rerank_documents(query, candidates, top_k=k)
        else:
            final_docs = candidates[:k]

        return final_docs

    # ─────────────────────────── RERANKING ────────────────────────────

    def rerank_documents(
        self,
        query: str,
        docs: List[Document],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """
        Rerank documents bằng Cross-Encoder.

        Args:
            query: Câu truy vấn
            docs: Danh sách document cần rerank
            top_k: Số document giữ lại sau rerank (None = giữ tất cả)

        Returns:
            Danh sách document đã được sắp xếp lại, có thêm 'rerank_score' trong metadata
        """
        if not docs or self.reranker is None:
            return docs

        pairs = [(query, doc.page_content) for doc in docs]
        raw_scores = self.reranker.predict(pairs)
        # atleast_1d đảm bảo an toàn khi chỉ có 1 doc (scalar → array)
        scores = np.atleast_1d(raw_scores).tolist()

        # Gắn rerank_score vào metadata và sắp xếp
        scored_docs = sorted(
            zip(scores, docs),
            key=lambda x: x[0],
            reverse=True
        )

        result = []
        for score, doc in scored_docs:
            doc.metadata["rerank_score"] = round(float(score), 4)
            result.append(doc)

        return result[:top_k] if top_k else result

    # ─────────────────────────── RETRIEVAL ────────────────────────────

    def parse_search_params(self, query: str) -> Tuple[str, int]:
        """Phân tích câu hỏi để tìm tham số tìm kiếm"""
        q_lower = query.lower()

        # Pattern 1: "Top N ..."
        top_match = re.search(r'top\s*(\d+)', q_lower)
        if top_match:
            k = max(1, min(int(top_match.group(1)), 10))
            clean_query = re.sub(r'top\s*\d+\s*', '', query, flags=re.IGNORECASE).strip()
            return clean_query, k

        # Pattern 2: "Tìm/Lấy/Cho N ..."
        action_match = re.search(r'(tìm|lấy|cho|hiện thị|xem)\s+(\d+)', q_lower)
        if action_match:
            k = max(1, min(int(action_match.group(2)), 10))
            clean_query = re.sub(
                r'(tìm|lấy|cho|hiện thị|xem)\s+\d+\s*', '', query, flags=re.IGNORECASE
            ).strip()
            return clean_query, k

        # Pattern 3: "N + từ khoá"
        k_match = re.search(
            r'(\d+)\s*(bài báo|bài|document|doc|tài liệu|kết quả|nguồn)', q_lower
        )
        if k_match:
            k = max(1, min(int(k_match.group(1)), 10))
            clean_query = re.sub(
                r'\d+\s*(bài báo|bài|document|doc|tài liệu|kết quả|nguồn)\s*',
                '', query, flags=re.IGNORECASE
            ).strip()
            return clean_query, k

        # Pattern 4: Keywords mức độ chi tiết
        detail_keywords = ['chi tiết', 'đầy đủ', 'nhiều thông tin', 'toàn diện', 'sâu', 'kỹ lưỡng']
        summary_keywords = ['tóm tắt', 'ngắn gọn', 'nhanh', 'vắn tắt', 'sơ lược', 'tổng quan nhanh']

        if any(word in q_lower for word in detail_keywords):
            return query, 5
        elif any(word in q_lower for word in summary_keywords):
            return query, 2

        return query, self.default_k

    def retrieve_and_rerank(
        self,
        query: str,
        k: int
    ) -> List[Document]:
        """
        Retrieve nhiều documents rồi rerank, trả về top-k.
        Tự động dùng hybrid search nếu use_hybrid=True.
        """
        # Nếu hybrid mode → dùng hybrid_retrieve_and_rerank
        if self.use_hybrid and hasattr(self, "bm25"):
            return self.hybrid_retrieve_and_rerank(query, k)

        # ── Fallback: Dense-only (giống cũ) ──────────────────────────────
        retrieve_k = min(k * self.retrieval_multiplier, self.db.index.ntotal)
        retrieve_k = max(retrieve_k, k)

        docs_and_scores = self.db.similarity_search_with_score(query, k=retrieve_k)

        retrieved_docs = []
        for doc, score in docs_and_scores:
            doc.metadata["similarity_score"] = round(float(1 / (1 + score)), 4)
            doc.metadata["faiss_distance"] = round(float(score), 4)
            retrieved_docs.append(doc)

        if self.use_reranker and self.reranker and len(retrieved_docs) > 1:
            reranked_docs = self.rerank_documents(query, retrieved_docs, top_k=k)
            return reranked_docs
        else:
            return retrieved_docs[:k]

    def enhanced_search(self, query: str) -> Tuple[Dict[str, Any], int]:
        """
        Thực hiện tìm kiếm RAG đầy đủ: parse → retrieve → rerank → generate.

        Args:
            query: Câu hỏi đầu vào

        Returns:
            Tuple[Dict, int]: (result_dict, used_k)
            result_dict có keys: "answer", "context"
        """
        clean_query, k = self.parse_search_params(query)

        # Retrieve + Rerank
        top_docs = self.retrieve_and_rerank(clean_query, k)

        # Generate answer
        answer = self.combine_docs_chain.invoke({
            "input": clean_query,
            "context": top_docs
        })

        result = {
            "answer": answer,
            "context": top_docs
        }

        return result, k

    # ─────────────────────────── UTILITIES ────────────────────────────

    def set_default_k(self, k: int):
        """Cài đặt số document mặc định"""
        self.default_k = max(1, min(k, 10))
        print(f"✅ Đã cập nhật số document mặc định: {self.default_k}")

    def get_database_info(self) -> Dict[str, Any]:
        """Lấy thông tin về database"""
        return {
            "db_dir": self.db_dir,
            "total_vectors": self.db.index.ntotal,
            "embedding_model": self.embeddings.model_name,
            "default_k": self.default_k,
            "reranker_enabled": self.use_reranker,
        }

    def search_with_similarity_scores(self, query: str, k: int = None) -> list:
        """Tìm kiếm với điểm similarity"""
        if k is None:
            k = self.default_k
        docs_and_scores = self.db.similarity_search_with_score(query, k=k)
        return docs_and_scores

    # ─────────────────────────── INTERACTIVE ──────────────────────────

    def run_interactive(self):
        """Chạy chế độ interactive chatbot"""
        print("=" * 60)
        print("🤖 RAG CHATBOT - Interactive Mode")
        print("=" * 60)
        print(f"📁 Database: {self.db_dir}")
        print(f"🔢 Default k: {self.default_k}")
        print(f"📊 Total documents: {self.db.index.ntotal}")
        print(f"🔄 Reranker: {'enabled' if self.use_reranker else 'disabled'}")
        print(f"🔀 Hybrid Search: {'enabled' if self.use_hybrid else 'disabled'}")
        print("\n📋 Available commands:")
        print("- 'exit'/'quit': Thoát chương trình")
        print("- 'config k=N': Thay đổi số document mặc định")
        print("- 'config hybrid=on/off': Bật/tắt hybrid search")
        print("- 'info': Xem thông tin database")
        print("- 'similarity <query>': Tìm kiếm với điểm similarity\n")

        while True:
            try:
                query = input("💬 Câu hỏi: ").strip()

                if not query:
                    continue

                if query.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt!")
                    break

                if query.lower().startswith("config "):
                    try:
                        config_param = query[7:].strip()
                        if config_param.startswith("k="):
                            self.set_default_k(int(config_param[2:]))
                        elif config_param.startswith("hybrid="):
                            val = config_param[7:].lower()
                            self.use_hybrid = val in ("on", "true", "1")
                            print(f"✅ Hybrid search: {'enabled' if self.use_hybrid else 'disabled'}")
                        else:
                            print("❌ Lệnh config không hợp lệ. Dùng: config k=5 | config hybrid=on")
                    except ValueError:
                        print("❌ Giá trị không hợp lệ")
                    continue

                if query.lower() == "info":
                    info = self.get_database_info()
                    print(f"\n📊 Thông tin Database: {info}\n")
                    continue

                if query.lower().startswith("similarity "):
                    search_query = query[11:].strip()
                    docs_and_scores = self.search_with_similarity_scores(search_query, k=5)
                    for i, (doc, score) in enumerate(docs_and_scores, 1):
                        print(f"\n📄 #{i}: FAISS distance = {score:.4f}")
                        print(f"   URL: {doc.metadata.get('id', 'N/A')}")
                        print(f"   Content: {doc.page_content[:150]}...")
                    continue

                # RAG search
                mode_label = "Hybrid (FAISS+BM25)" if self.use_hybrid else "Dense (FAISS only)"
                print(f"\n⏳ [{mode_label}] Processing: '{query}'")
                start_time = time.time()

                result, used_k = self.enhanced_search(query)
                elapsed = time.time() - start_time

                print(f"\n✅ Trả lời (dựa trên {used_k} documents):")
                print("-" * 50)
                print(result["answer"])
                print("-" * 50)

                print(f"\n📚 Nguồn tham khảo:")
                for i, doc in enumerate(result["context"], 1):
                    rerank_score = doc.metadata.get("rerank_score", "N/A")
                    sim_score = doc.metadata.get("similarity_score", "N/A")
                    rrf_score = doc.metadata.get("rrf_score", "N/A")
                    bm25_score = doc.metadata.get("bm25_score", "N/A")
                    print(f"   📄 Document {i}:")
                    print(f"      URL: {doc.metadata.get('id', 'N/A')}")
                    print(f"      FAISS similarity: {sim_score}")
                    if self.use_hybrid:
                        print(f"      BM25 score:       {bm25_score}")
                        print(f"      RRF score:        {rrf_score}")
                    if self.use_reranker:
                        print(f"      Rerank score:     {rerank_score}")

                print(f"\n⏱️ Thời gian xử lý: {elapsed:.2f}s | Documents sử dụng: {used_k}")
                print("=" * 60)

            except KeyboardInterrupt:
                print("\n👋 Tạm biệt!")
                break
            except Exception as e:
                print(f"❌ Lỗi: {str(e)}")
                continue


def main():
    parser = argparse.ArgumentParser(description="RAG Chatbot với FAISS + BM25 Hybrid + Reranking")

    parser.add_argument("--db", type=str, default="faiss_news_db_ivf",
                        help="Đường dẫn FAISS database directory")
    parser.add_argument("--api-key", type=str, default="",
                        help="OpenAI API key")
    parser.add_argument("--no-reranker", action="store_true",
                        help="Tắt cross-encoder reranker")
    parser.add_argument("--no-hybrid", action="store_true",
                        help="Tắt hybrid search (chỉ dùng FAISS)")
    parser.add_argument("--hybrid-alpha", type=float, default=0.5,
                        help="Trọng số FAISS trong RRF (0.0~1.0, mặc định 0.5)")
    parser.add_argument("--default-k", type=int, default=3,
                        help="Số document mặc định để retrieve")
    parser.add_argument("--list-db", action="store_true",
                        help="Liệt kê các FAISS databases có sẵn")

    args = parser.parse_args()

    if args.list_db:
        print("📁 Available FAISS databases:")
        current_dir = os.getcwd()
        faiss_dirs = [d for d in os.listdir(current_dir)
                      if os.path.isdir(d) and ('faiss' in d.lower() or 'db' in d.lower())]
        for i, d in enumerate(faiss_dirs, 1):
            print(f"   {i}. {d}")
        return

    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OpenAI API key is required")
        return

    if not os.path.exists(args.db):
        print(f"❌ Error: Database directory not found: {args.db}")
        return

    try:
        chatbot = RAGChatbot(
            db_dir=args.db,
            api_key=api_key,
            use_reranker=not args.no_reranker,
            use_hybrid=not args.no_hybrid,
            hybrid_alpha=args.hybrid_alpha,
        )
        chatbot.set_default_k(args.default_k)
        chatbot.run_interactive()
    except Exception as e:
        print(f"❌ Error initializing chatbot: {str(e)}")


if __name__ == "__main__":
    main()






import argparse
import os
import re
import time
from typing import Tuple, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain


class RAGChatbot:
    def __init__(self, db_dir: str = "faiss_news_db_ivf", api_key: str = ""):
        """
        Args:
            db_dir (str): Đường dẫn đến thư mục FAISS database
            api_key (str): OpenAI API key
        """
        self.db_dir = db_dir
        self.api_key = api_key
        self.default_k = 3

        # Initialize components
        self._init_embeddings()
        self._load_database()
        self._init_llm()
        self._init_prompt()
        self._create_chains()

        print(f"✅ RAG Chatbot initialized with database: {db_dir}")

    def _init_embeddings(self):
        """Khởi tạo embedding model"""
        print("🔄 Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print("✅ Embedding model loaded")

    def _load_database(self):
        """Load FAISS database"""
        if not os.path.exists(self.db_dir):
            raise FileNotFoundError(f"Database directory not found: {self.db_dir}")

        print(f"🔄 Loading FAISS database from: {self.db_dir}")
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

        print("🔄 Initializing LLM...")
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
            template="""
        Bạn là một trợ lý thông minh. Dưới đây là ngữ cảnh từ báo chí:
        
        {context}
        
        Câu hỏi: {input}
        
        Hãy trả lời ngắn gọn, chính xác dựa trên ngữ cảnh. 
        Nếu không có thông tin, hãy nói: "Tôi không có thông tin trong dữ liệu."
        """
        )

    def _create_chains(self):
        """Tạo chains"""
        self.combine_docs_chain = create_stuff_documents_chain(self.llm, self.qa_prompt)

    def create_dynamic_retrieval_chain(self, k: int = 3):
        """
        Tạo retrieval chain với số document tùy chỉnh

        Args:
            k (int): Số lượng document để retrieve

        Returns:
            Retrieval chain
        """
        retriever = self.db.as_retriever(search_kwargs={"k": k})
        return create_retrieval_chain(retriever, self.combine_docs_chain)

    def parse_search_params(self, query: str) -> Tuple[str, int]:
        """
        Phân tích câu hỏi để tìm tham số tìm kiếm

        Args:
            query (str): Câu hỏi đầu vào

        Returns:
            Tuple[str, int]: (clean_query, k)
        """
        q_lower = query.lower()

        # Pattern 1: "Top N ..."
        top_match = re.search(r'top\s*(\d+)', q_lower)
        if top_match:
            k = int(top_match.group(1))
            k = max(1, min(k, 10))
            clean_query = re.sub(r'top\s*\d+\s*', '', query, flags=re.IGNORECASE).strip()
            return clean_query, k

        # Pattern 2: "Tìm/Lấy/Cho N ..."
        action_match = re.search(r'(tìm|lấy|cho|hiển thị|xem)\s+(\d+)', q_lower)
        if action_match:
            k = int(action_match.group(2))
            k = max(1, min(k, 10))
            clean_query = re.sub(r'(tìm|lấy|cho|hiển thị|xem)\s+\d+\s*', '', query, flags=re.IGNORECASE).strip()
            return clean_query, k

        # Pattern 3: "N + từ khóa"
        k_match = re.search(r'(\d+)\s*(bài báo|bài|document|doc|tài liệu|kết quả|nguồn)', q_lower)
        if k_match:
            k = int(k_match.group(1))
            k = max(1, min(k, 10))
            clean_query = re.sub(r'\d+\s*(bài báo|bài|document|doc|tài liệu|kết quả|nguồn)\s*', '', query,
                                 flags=re.IGNORECASE).strip()
            return clean_query, k

        # Pattern 4: Keywords cho mức độ chi tiết
        detail_keywords = ['chi tiết', 'đầy đủ', 'nhiều thông tin', 'toàn diện', 'sâu', 'kỹ lưỡng']
        summary_keywords = ['tóm tắt', 'ngắn gọn', 'nhanh', 'vắn tắt', 'sơ lược', 'tổng quan nhanh']

        if any(word in q_lower for word in detail_keywords):
            return query, 5
        elif any(word in q_lower for word in summary_keywords):
            return query, 2

        return query, self.default_k

    def enhanced_search(self, query: str) -> Tuple[Dict[str, Any], int]:
        """
        Thực hiện tìm kiếm với tham số động

        Args:
            query (str): Câu hỏi đầu vào

        Returns:
            Tuple[Dict, int]: (result, used_k)
        """
        clean_query, k = self.parse_search_params(query)

        # Tạo retrieval chain với k tương ứng
        retrieval_chain = self.create_dynamic_retrieval_chain(k)

        result = retrieval_chain.invoke({"input": clean_query})
        return result, k

    def set_default_k(self, k: int):
        """
        Cài đặt số document mặc định

        Args:
            k (int): Số document mặc định
        """
        self.default_k = max(1, min(k, 10))
        print(f"✅ Đã cập nhật số document mặc định: {self.default_k}")

    def get_database_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về database

        Returns:
            Dict với thông tin database
        """
        return {
            "db_dir": self.db_dir,
            "total_vectors": self.db.index.ntotal,
            "embedding_model": self.embeddings.model_name,
            "default_k": self.default_k
        }

    def search_with_similarity_scores(self, query: str, k: int = None) -> list:
        """
        Tìm kiếm với điểm similarity

        Args:
            query (str): Câu hỏi
            k (int): Số document (None để dùng mặc định)

        Returns:
            List các document với điểm số
        """
        if k is None:
            k = self.default_k

        docs_and_scores = self.db.similarity_search_with_score(query, k=k)
        return docs_and_scores

    def run_interactive(self):
        """
        Chạy chế độ interactive chatbot
        """
        print("=" * 60)
        print("🤖 RAG CHATBOT - Interactive Mode")
        print("=" * 60)
        print(f"📊 Database: {self.db_dir}")
        print(f"🔢 Default k: {self.default_k}")
        print(f"📚 Total documents: {self.db.index.ntotal}")
        print("\n📝 Available commands:")
        print("- 'exit' hoặc 'quit': Thoát chương trình")
        print("- 'config k=N': Thay đổi số document mặc định")
        print("- 'info': Xem thông tin database")
        print("- 'similarity <query>': Tìm kiếm với điểm similarity")
        print("\n💡 Ví dụ câu hỏi:")
        print("- 'Tìm 5 document về AI'")
        print("- 'Top 3 bài về kinh tế'")
        print("- 'Cho tôi thông tin chi tiết về blockchain'\n")

        while True:
            try:
                query = input("🔍 Câu hỏi: ").strip()

                if not query:
                    continue

                # Lệnh thoát
                if query.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt!")
                    break

                # Lệnh config
                if query.lower().startswith("config "):
                    try:
                        config_param = query[7:].strip()
                        if config_param.startswith("k="):
                            new_k = int(config_param[2:])
                            self.set_default_k(new_k)
                            continue
                        else:
                            print("❌ Lệnh config không hợp lệ. Sử dụng: config k=5")
                            continue
                    except ValueError:
                        print("❌ Giá trị k phải là số nguyên")
                        continue

                # Lệnh info
                if query.lower() == "info":
                    info = self.get_database_info()
                    print(f"\n📊 Thông tin Database:")
                    print(f"   📁 Directory: {info['db_dir']}")
                    print(f"   🔢 Total vectors: {info['total_vectors']}")
                    print(f"   🤖 Embedding model: {info['embedding_model']}")
                    print(f"   ⚙️ Default k: {info['default_k']}\n")
                    continue

                # Lệnh similarity
                if query.lower().startswith("similarity "):
                    search_query = query[11:].strip()
                    if not search_query:
                        print("❌ Vui lòng nhập query để tìm kiếm")
                        continue

                    print(f"\n🔍 Similarity search cho: '{search_query}'")
                    docs_and_scores = self.search_with_similarity_scores(search_query, k=5)

                    for i, (doc, score) in enumerate(docs_and_scores, 1):
                        print(f"\n📄 #{i}: Score = {score:.4f}")
                        print(f"   URL: {doc.metadata.get('id', 'N/A')}")
                        print(f"   Content: {doc.page_content[:150]}...")
                    continue

                # Tìm kiếm thường
                print(f"\n🔄 Processing query: '{query}'")
                start_time = time.time()

                result, used_k = self.enhanced_search(query)

                end_time = time.time()

                # Hiển thị kết quả
                print(f"\n🤖 Trả lời (dựa trên {used_k} documents):")
                print("-" * 50)
                print(result["answer"])
                print("-" * 50)

                print(f"\n📚 Nguồn tham khảo:")
                for i, doc in enumerate(result["context"], 1):
                    print(f"   📄 Document {i}:")
                    print(f"      URL: {doc.metadata.get('id', 'N/A')}")
                    if hasattr(doc, 'score'):
                        print(f"      Độ liên quan: {doc.score:.3f}")

                print(f"\n⏱️ Thời gian xử lý: {end_time - start_time:.2f}s")
                print(f"📊 Số documents sử dụng: {used_k}")
                print("=" * 60)

            except KeyboardInterrupt:
                print("\n👋 Tạm biệt!")
                break
            except Exception as e:
                print(f"❌ Lỗi: {str(e)}")
                continue


def main():
    """
    Main function với argument parsing
    """
    parser = argparse.ArgumentParser(description="RAG Chatbot với FAISS")

    parser.add_argument(
        "--db",
        type=str,
        default="faiss_news_db_ivf",
        help="Đường dẫn đến FAISS database directory (default: faiss_news_db_ivf)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="OpenAI API key (nếu không truyền sẽ lấy từ environment variable OPENAI_API_KEY)"
    )

    parser.add_argument(
        "--list-db",
        action="store_true",
        help="Liệt kê các database FAISS có sẵn"
    )

    parser.add_argument(
        "--default-k",
        type=int,
        default=3,
        help="Số document mặc định để retrieve (default: 3)"
    )

    args = parser.parse_args()

    # Liệt kê databases nếu được yêu cầu
    if args.list_db:
        print("📁 Available FAISS databases:")
        current_dir = os.getcwd()
        faiss_dirs = [d for d in os.listdir(current_dir)
                      if os.path.isdir(d) and ('faiss' in d.lower() or 'db' in d.lower())]

        if faiss_dirs:
            for i, db_dir in enumerate(faiss_dirs, 1):
                print(f"   {i}. {db_dir}")
        else:
            print("   No FAISS databases found in current directory")
        return

    # Lấy API key từ environment nếu không được truyền
    api_key = args.api_key
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ Error: OpenAI API key is required")
            print("   Use --api-key argument or set OPENAI_API_KEY environment variable")
            return

    # Kiểm tra database directory
    if not os.path.exists(args.db):
        print(f"❌ Error: Database directory not found: {args.db}")
        print("\n💡 Available options:")
        print("   1. Use --list-db to see available databases")
        print("   2. Specify correct path with --db argument")
        return

    try:
        # Khởi tạo chatbot
        print(f"🚀 Initializing RAG Chatbot...")
        print(f"   Database: {args.db}")
        print(f"   Default k: {args.default_k}")

        chatbot = RAGChatbot(db_dir=args.db, api_key=api_key)
        chatbot.set_default_k(args.default_k)

        chatbot.run_interactive()

    except Exception as e:
        print(f"❌ Error initializing chatbot: {str(e)}")


if __name__ == "__main__":
    main()
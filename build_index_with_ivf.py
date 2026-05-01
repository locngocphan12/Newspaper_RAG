import os
import json
import faiss
import pickle
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.in_memory import InMemoryDocstore
import numpy as np

DATA_DIR = "E:\\pythonProject\\NewspaperRAG\\NewspaperRAG\\data"
DB_DIR = "faiss_news_db_ivf"


def load_all_documents(data_dir=DATA_DIR):
    """Load all documents from JSON files"""
    docs = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item_id, item_data in data.items():
                            # Kiểm tra xem có context không
                            if 'context' not in item_data or not item_data['context']:
                                continue

                            content = " ".join(item_data['context'])
                            if len(content.strip()) == 0:  # Skip empty content
                                continue

                            docs.append(
                                Document(
                                    page_content=content,
                                    metadata={
                                        "id": item_id,
                                        "section": item_data.get("section", ""),
                                        "subsection": item_data.get("subsection", ""),
                                        "source_file": file
                                    }
                                )
                            )
                except Exception as e:
                    print(f"Lỗi đọc {file_path}: {e}")
    return docs


def create_ivf_faiss_db(chunks, embeddings, nlist=100, nprobe=10):
    """Create IVF FAISS index from chunks"""
    if not chunks:
        raise ValueError("No chunks provided")

    # Extract texts
    texts = [chunk.page_content for chunk in chunks]

    # Generate embeddings
    print("Generating embeddings...")
    vectors = embeddings.embed_documents(texts)
    vectors = np.array(vectors, dtype=np.float32)
    dim = vectors.shape[1]

    print(f"Vector dimension: {dim}, Count: {len(vectors)}")

    # Adjust nlist based on data size
    # Rule of thumb: nlist should be sqrt(n) to 4*sqrt(n)
    n_vectors = len(vectors)
    if n_vectors < 1000:
        nlist = min(nlist, n_vectors // 4)  # At least 4 vectors per cluster

    print(f"Using nlist: {nlist}")

    # Create IVF index
    quantizer = faiss.IndexFlatL2(dim)
    index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)

    # Train index
    print("Training IVF index...")
    index.train(vectors)
    print("Training completed")

    # Add vectors
    index.add(vectors)
    index.nprobe = nprobe

    print(f"Added {index.ntotal} vectors to IVF index")

    # Create docstore
    docstore = InMemoryDocstore({str(i): chunks[i] for i in range(len(chunks))})
    index_to_docstore_id = {i: str(i) for i in range(len(chunks))}

    # Create FAISS vectorstore
    vectorstore = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id
    )

    return vectorstore


def save_faiss_db(vectorstore, embeddings, db_dir):
    """Save FAISS database and associated metadata"""
    os.makedirs(db_dir, exist_ok=True)

    # Save the vectorstore (includes index, docstore, mappings)
    vectorstore.save_local(db_dir)

    # Save additional metadata
    metadata = {
        "embedding_model": embeddings.model_name,
        "index_type": "IVF",
        "nprobe": vectorstore.index.nprobe,
        "nlist": vectorstore.index.nlist,
        "ntotal": vectorstore.index.ntotal
    }

    with open(os.path.join(db_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved FAISS database to {db_dir}")


def load_faiss_db(db_dir, embeddings=None):
    """Load FAISS database from directory"""
    if embeddings is None:
        # Load metadata to get embedding model
        with open(os.path.join(db_dir, "metadata.json"), "r", encoding="utf-8") as f:
            metadata = json.load(f)

        embeddings = HuggingFaceEmbeddings(
            model_name=metadata["embedding_model"]
        )

    vectorstore = FAISS.load_local(
        db_dir,
        embeddings,
        allow_dangerous_deserialization=True  # Cần thiết cho pickle
    )

    return vectorstore


def main():
    # 1. Load documents
    print("Loading documents...")
    docs = load_all_documents()

    if not docs:
        print("❌ No documents found!")
        return

    print(f"Loaded {len(docs)} documents")

    # 2. Split into chunks
    print("Splitting documents...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=60,
        separators=["\n\n", "\n", ". ", "! ", "? "]
    )
    chunks = splitter.split_documents(docs)

    if not chunks:
        print("❌ No chunks created!")
        return

    print(f"Created {len(chunks)} chunks")

    # 3. Initialize embeddings
    print("Initializing embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    # 4. Create FAISS database
    try:
        vectorstore = create_ivf_faiss_db(chunks, embeddings, nlist=100, nprobe=10)

        # 5. Save database
        save_faiss_db(vectorstore, embeddings, DB_DIR)

        # 6. Test search
        print("\nTesting search...")
        results = vectorstore.similarity_search("tin tức", k=3)
        for i, doc in enumerate(results):
            print(f"Result {i + 1}: {doc.page_content[:100]}...")

    except Exception as e:
        print(f"❌ Error creating FAISS database: {e}")
        raise


def test_load():
    """Test loading the saved database"""
    print("Testing database loading...")
    try:
        vectorstore = load_faiss_db(DB_DIR)
        print("✅ Database loaded successfully")

        # Test search
        results = vectorstore.similarity_search("chính trị", k=2)
        print(f"Search returned {len(results)} results")

    except Exception as e:
        print(f"❌ Error loading database: {e}")


if __name__ == "__main__":
    main()


    # test_load()
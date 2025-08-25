import json, os, re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

data_path = "D:\\pythonProject\\Top10-Article\\DanTri\\an-sinhp.json"
DB_DIR = "faiss_news_db"
def load_documents():
    docs = []
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        content = " ".join(data[item]['context'])
        docs.append(Document(
            page_content=content,
            metadata={"id": item, "section": data[item]["section"], "subsection": data[item]["subsection"]}
        ))
    return docs

def main():
    docs = load_documents()
    print(f"Loaded {len(docs)} articles")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=60, separators=["\n\n", "\n", ". "]
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    db = FAISS.from_documents(chunks, embeddings)
    os.makedirs(DB_DIR, exist_ok=True)
    db.save_local(DB_DIR)
    print(f"✅ Saved FAISS DB to ./{DB_DIR}")
if __name__ == "__main__":
    main()
import json, os, re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

DB_DIR = "faiss_news_db"

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
db = FAISS.load_local(DB_DIR, embeddings, allow_dangerous_deserialization=True)

query = "Chính phủ có chính sách mới nào về giáo dục?"
docs = db.similarity_search(query, k=3)

print(docs)
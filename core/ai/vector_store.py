import chromadb
import os
from django.conf import settings

class VectorStoreManager:
    def __init__(self):
        # Stores the DB in 'chroma_db' folder in your project root
        db_path = os.path.join(settings.BASE_DIR, "chroma_db")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="resume_embeddings")

    def add_resume_chunks(self, resume_id, chunks, embeddings):
        if not chunks or not embeddings:
            return

        # Create unique IDs: "resume_1_chunk_0", etc.
        ids = [f"resume_{resume_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"resume_id": str(resume_id)} for _ in chunks]

        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Added {len(chunks)} chunks to Vector Store for Resume {resume_id}")

    def search_similar(self, query_embedding, n_results=5):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
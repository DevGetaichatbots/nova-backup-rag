import json
from src.database import create_vector_table, insert_embeddings, similarity_search
from src.embeddings import generate_embeddings, generate_single_embedding
from src.pdf_processor import process_pdf_binary
from src.config import settings


class VectorStoreManager:
    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION
    
    def create_store_from_pdf(self, session_id: str, file_name: str, pdf_bytes: bytes) -> dict:
        table_name = f"vs_{session_id}_{file_name.replace('.', '_').replace(' ', '_')}"
        table_name = table_name[:63]
        
        safe_table_name = create_vector_table(table_name, self.dimension)
        
        chunks = process_pdf_binary(pdf_bytes, filename=file_name)
        
        if not chunks:
            return {
                "status": "error",
                "message": "No text content found in PDF",
                "table_name": safe_table_name
            }
        
        texts = [chunk["content"] for chunk in chunks]
        embeddings = generate_embeddings(texts)
        
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                "content": chunk["content"],
                "embedding": embeddings[i],
                "metadata": json.dumps(chunk["metadata"])
            })
        
        insert_embeddings(safe_table_name, documents)
        
        return {
            "status": "success",
            "table_name": safe_table_name,
            "chunks_processed": len(chunks),
            "message": f"Successfully stored {len(chunks)} chunks in vector store"
        }
    
    def search(self, table_name: str, query: str, top_k: int = 10) -> list[dict]:
        query_embedding = generate_single_embedding(query)
        results = similarity_search(table_name, query_embedding, top_k)
        
        return [
            {
                "content": r["content"],
                "similarity": float(r["similarity"]),
                "metadata": r["metadata"] if r["metadata"] else {}
            }
            for r in results
        ]
    
    def search_multiple_stores(self, table_names: list[str], query: str, top_k: int = 10) -> dict:
        query_embedding = generate_single_embedding(query)
        
        all_results = {}
        for table_name in table_names:
            try:
                results = similarity_search(table_name, query_embedding, top_k)
                all_results[table_name] = [
                    {
                        "content": r["content"],
                        "similarity": float(r["similarity"]),
                        "metadata": r["metadata"] if r["metadata"] else {}
                    }
                    for r in results
                ]
            except Exception as e:
                all_results[table_name] = {"error": str(e)}
        
        return all_results


vector_store_manager = VectorStoreManager()

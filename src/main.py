from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

from src.vector_store import vector_store_manager
from src.agent import rag_agent
from src.database import init_pgvector_extension, create_chat_memory_table

app = FastAPI(
    title="RAG Agent SaaS",
    description="Azure AI RAG Agent with Supabase pgvector - Upload PDFs and query with AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    vs_tables: List[str]
    session_id: str
    top_k: Optional[int] = 10


class QueryResponse(BaseModel):
    response: str
    sources: List[str]
    context_chunks: int


@app.on_event("startup")
async def startup_event():
    try:
        init_pgvector_extension()
        create_chat_memory_table()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")


@app.get("/")
async def root():
    return {
        "message": "RAG Agent SaaS API",
        "endpoints": {
            "upload": "POST /upload - Upload PDF and create vector store",
            "query": "POST /query - Query the AI agent",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        pdf_bytes = await file.read()
        
        result = vector_store_manager.create_store_from_pdf(
            session_id=session_id,
            file_name=filename,
            pdf_bytes=pdf_bytes
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    if not request.vs_tables:
        raise HTTPException(status_code=400, detail="At least one vector store table is required")
    
    try:
        result = rag_agent.query(
            user_query=request.query,
            table_names=request.vs_tables,
            session_id=request.session_id,
            top_k=request.top_k or 10
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

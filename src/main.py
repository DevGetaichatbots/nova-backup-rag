from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

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


@app.on_event("startup")
async def startup_event():
    try:
        init_pgvector_extension()
        create_chat_memory_table()
        print("Database initialized successfully")
        
        from src.azure_ocr import AzureDocumentIntelligence
        is_valid, msg = AzureDocumentIntelligence.check_credentials()
        if is_valid:
            print("Azure Document Intelligence OCR: Ready")
        else:
            raise ValueError(f"Azure OCR required but not configured: {msg}")
    except Exception as e:
        print(f"Startup error: {e}")
        raise


@app.get("/")
async def root():
    return {
        "message": "RAG Agent SaaS API",
        "endpoints": {
            "upload": "POST /upload - Upload 2 PDF schedules",
            "query": "POST /query - Query the AI agent",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_schedules(
    session_id: str = Form(...),
    old_session_id: str = Form(...),
    new_session_id: str = Form(...),
    old_schedule: UploadFile = File(...),
    new_schedule: UploadFile = File(...)
):
    logger.info(f"=== UPLOAD REQUEST ===")
    logger.info(f"Session: {session_id}")
    logger.info(f"Old schedule: {old_schedule.filename} -> table: {old_session_id}")
    logger.info(f"New schedule: {new_schedule.filename} -> table: {new_session_id}")
    
    old_filename = old_schedule.filename or "old_schedule.pdf"
    new_filename = new_schedule.filename or "new_schedule.pdf"
    
    if not old_filename.lower().endswith('.pdf') or not new_filename.lower().endswith('.pdf'):
        logger.error("Invalid file type - only PDF accepted")
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        old_pdf_bytes = await old_schedule.read()
        new_pdf_bytes = await new_schedule.read()
        logger.info(f"Files read: old={len(old_pdf_bytes)} bytes, new={len(new_pdf_bytes)} bytes")
        
        logger.info(f"Processing OLD schedule...")
        old_result = vector_store_manager.create_store_from_pdf(
            session_id=session_id,
            file_name=old_filename,
            pdf_bytes=old_pdf_bytes,
            table_name=old_session_id
        )
        logger.info(f"OLD schedule done: {old_result.get('chunks_processed', 0)} chunks")
        
        logger.info(f"Processing NEW schedule...")
        new_result = vector_store_manager.create_store_from_pdf(
            session_id=session_id,
            file_name=new_filename,
            pdf_bytes=new_pdf_bytes,
            table_name=new_session_id
        )
        logger.info(f"NEW schedule done: {new_result.get('chunks_processed', 0)} chunks")
        
        logger.info(f"=== UPLOAD COMPLETE ===")
        return {
            "status": "success",
            "session_id": session_id,
            "old_schedule": {
                "table_name": old_result.get("table_name"),
                "chunks": old_result.get("chunks_processed", 0)
            },
            "new_schedule": {
                "table_name": new_result.get("table_name"),
                "chunks": new_result.get("chunks_processed", 0)
            },
            "message": "Both schedules processed and stored successfully"
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_agent(
    query: str = Form(...),
    vs_table: str = Form(...),
    old_session_id: str = Form(...),
    new_session_id: str = Form(...),
    language: str = Form("en")
):
    logger.info(f"=== QUERY REQUEST ===")
    logger.info(f"Query: {query[:100]}{'...' if len(query) > 100 else ''}")
    logger.info(f"Session: {vs_table} | Language: {language}")
    logger.info(f"Vector stores: {old_session_id}, {new_session_id}")
    
    try:
        table_names = [old_session_id, new_session_id]
        
        result = rag_agent.query(
            user_query=query,
            table_names=table_names,
            session_id=vs_table,
            language=language,
            top_k=10
        )
        
        logger.info(f"Response generated: {len(result['response'])} chars, {result['context_chunks']} chunks used")
        logger.info(f"=== QUERY COMPLETE ===")
        
        return {
            "response": result["response"],
            "sources": result["sources"],
            "context_chunks": result["context_chunks"]
        }
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

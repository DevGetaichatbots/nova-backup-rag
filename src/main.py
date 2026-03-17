from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

_query_executor = ThreadPoolExecutor(max_workers=4)
_upload_progress: Dict[str, Dict[str, Any]] = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from src.vector_store import vector_store_manager
from src.agent import rag_agent
from src.predictive_agent import predictive_agent
from src.database import init_pgvector_extension, create_chat_memory_table, save_session_metadata, get_session_metadata
from src.html_formatter import format_response_as_html
from src.predictive_html_formatter import format_predictive_as_html

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
        
        upload_id = str(uuid.uuid4())[:8]
        _upload_progress[upload_id] = {
            "status": "processing",
            "upload_id": upload_id,
            "session_id": session_id,
            "old_filename": old_filename,
            "new_filename": new_filename,
            "started_at": time.time(),
            "old_schedule": {"step": "queued", "detail": "Waiting to start", "progress": 0},
            "new_schedule": {"step": "queued", "detail": "Waiting to start", "progress": 0},
            "overall_progress": 0
        }
        
        loop = asyncio.get_event_loop()
        
        async def _process_upload_background():
            try:
                def progress_cb(file_key, step, detail, progress):
                    _upload_progress[upload_id][file_key]["step"] = step
                    _upload_progress[upload_id][file_key]["detail"] = detail
                    _upload_progress[upload_id][file_key]["progress"] = progress
                    old_p = _upload_progress[upload_id]["old_schedule"]["progress"]
                    new_p = _upload_progress[upload_id]["new_schedule"]["progress"]
                    _upload_progress[upload_id]["overall_progress"] = (old_p + new_p) // 2

                def process_file(file_key, filename, pdf_bytes, table_id):
                    progress_cb(file_key, "ocr", f"Extracting content from {filename}...", 10)
                    result = vector_store_manager.create_store_from_pdf(
                        session_id, filename, pdf_bytes, table_id,
                        progress_callback=lambda step, detail, pct: progress_cb(file_key, step, detail, pct)
                    )
                    progress_cb(file_key, "complete", f"{filename} processed", 100)
                    return result
                
                old_future = loop.run_in_executor(
                    _query_executor,
                    lambda: process_file("old_schedule", old_filename, old_pdf_bytes, old_session_id)
                )
                new_future = loop.run_in_executor(
                    _query_executor,
                    lambda: process_file("new_schedule", new_filename, new_pdf_bytes, new_session_id)
                )
                
                old_result, new_result = await asyncio.gather(old_future, new_future)
                
                save_session_metadata(session_id, old_filename, new_filename, old_session_id, new_session_id)
                
                elapsed = time.time() - _upload_progress[upload_id]["started_at"]
                _upload_progress[upload_id].update({
                    "status": "complete",
                    "overall_progress": 100,
                    "elapsed_seconds": round(elapsed, 1),
                    "old_schedule": {
                        "step": "complete",
                        "detail": f"{old_result.get('chunks_processed', 0)} chunks stored",
                        "progress": 100,
                        "table_name": old_result.get("table_name"),
                        "chunks": old_result.get("chunks_processed", 0)
                    },
                    "new_schedule": {
                        "step": "complete",
                        "detail": f"{new_result.get('chunks_processed', 0)} chunks stored",
                        "progress": 100,
                        "table_name": new_result.get("table_name"),
                        "chunks": new_result.get("chunks_processed", 0)
                    }
                })
                logger.info(f"=== UPLOAD COMPLETE ({elapsed:.1f}s) ===")
                
            except Exception as e:
                logger.error(f"Upload failed: {e}")
                _upload_progress[upload_id].update({
                    "status": "error",
                    "error": str(e)
                })
        
        asyncio.create_task(_process_upload_background())
        
        return {
            "status": "processing",
            "upload_id": upload_id,
            "session_id": session_id,
            "message": f"Upload started. Poll GET /upload/progress/{upload_id} for real-time progress."
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/upload/progress/{upload_id}")
async def get_upload_progress(upload_id: str):
    if upload_id not in _upload_progress:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    return _upload_progress[upload_id]


DEV_HOSTS = [
    "a2f76a97-674f-4a1f-9ac6-c5bcb0c92fc9-00-jwtgkqguc1o3.worf.replit.dev",
]

@app.post("/query")
async def query_agent(
    request: Request,
    query: str = Form(...),
    vs_table: str = Form(...),
    old_session_id: str = Form(...),
    new_session_id: str = Form(...),
    language: str = Form("en"),
    format: str = Form(None)
):
    host = request.headers.get("host", "")
    is_dev = any(dev_host in host for dev_host in DEV_HOSTS)
    
    if format is None:
        format = "markdown" if is_dev else "html"
    
    logger.info(f"=== QUERY REQUEST ===")
    logger.info(f"Host: {host} | Is Dev: {is_dev}")
    logger.info(f"Query: {query[:100]}{'...' if len(query) > 100 else ''}")
    logger.info(f"Session: {vs_table} | Language: {language} | Format: {format}")
    logger.info(f"Vector stores: {old_session_id}, {new_session_id}")
    
    try:
        table_names = [old_session_id, new_session_id]
        
        session_meta = get_session_metadata(vs_table)
        old_filename = session_meta.get("old_filename", "Old Schedule")
        new_filename = session_meta.get("new_filename", "New Schedule")
        old_filename_clean = old_filename.replace(".pdf", "").replace(".PDF", "")
        new_filename_clean = new_filename.replace(".pdf", "").replace(".PDF", "")
        logger.info(f"  File names: {old_filename} / {new_filename}")
        
        is_comparison = rag_agent._is_comparison_query(query)
        logger.info(f"  Query type: {'comparison' if is_comparison else 'conversational'}")
        
        loop = asyncio.get_event_loop()
        
        if is_comparison:
            context = await loop.run_in_executor(
                _query_executor,
                lambda: rag_agent._retrieve_context(query, table_names, old_filename=old_filename, new_filename=new_filename)
            )
            
            logger.info(f"  Running comparison + predictive in parallel...")
            
            async def _run_comparison():
                return await loop.run_in_executor(
                    _query_executor,
                    lambda: rag_agent.query(
                        user_query=query,
                        table_names=table_names,
                        session_id=vs_table,
                        language=language,
                        top_k=10,
                        preloaded_context=context,
                        old_filename=old_filename_clean,
                        new_filename=new_filename_clean
                    )
                )
            
            async def _run_predictive():
                return await loop.run_in_executor(
                    _query_executor,
                    lambda: predictive_agent.analyze(
                        context=context,
                        user_query=query,
                        language=language,
                        old_filename=old_filename_clean,
                        new_filename=new_filename_clean
                    )
                )
            
            comparison_result, predictive_result = await asyncio.gather(
                _run_comparison(),
                _run_predictive(),
                return_exceptions=True
            )
            
            if isinstance(comparison_result, Exception):
                logger.error(f"  Comparison agent failed: {comparison_result}")
                raise comparison_result
            
            result = comparison_result
            
            if isinstance(predictive_result, Exception):
                logger.error(f"  Predictive agent failed: {predictive_result}")
                predictive_text = ""
                predictive_status = "error"
                predictive_model = ""
            else:
                predictive_text = predictive_result.get("predictive_insights", "")
                predictive_status = predictive_result.get("status", "error")
                predictive_model = predictive_result.get("model", "")
            
            if format == "html" and predictive_text:
                predictive_text = format_predictive_as_html(predictive_text, language)
            
            logger.info(f"  Predictive complete: {len(predictive_text)} chars, status: {predictive_status}")
        else:
            result = await loop.run_in_executor(
                _query_executor,
                lambda: rag_agent.query(
                    user_query=query,
                    table_names=table_names,
                    session_id=vs_table,
                    language=language,
                    top_k=10,
                    old_filename=old_filename_clean,
                    new_filename=new_filename_clean
                )
            )
            predictive_text = None
            predictive_status = None
            predictive_model = None
        
        response_text = result["response"]
        
        if format == "html" and is_comparison:
            logger.info(f"Converting to HTML format...")
            response_text = format_response_as_html(response_text, language)
        elif format == "html" and not is_comparison:
            logger.info(f"Conversational response - wrapping in simple HTML...")
            response_text = f'<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; padding: 20px; color: #0f172a; line-height: 1.6; font-size: 15px;">{response_text}</div>'
        
        logger.info(f"Response generated: {len(response_text)} chars, {result['context_chunks']} chunks used")
        logger.info(f"=== QUERY COMPLETE ===")
        
        response_payload = {
            "response": response_text,
            "sources": result["sources"],
            "context_chunks": result["context_chunks"],
            "format": format
        }
        
        if is_comparison:
            response_payload["predictive_insights"] = predictive_text or ""
            response_payload["predictive_status"] = predictive_status
            response_payload["predictive_model"] = predictive_model or ""
        
        return response_payload
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

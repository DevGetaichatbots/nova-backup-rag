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
_predictive_results: Dict[str, Dict[str, Any]] = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from src.vector_store import vector_store_manager
from src.agent import rag_agent
from src.predictive_agent import predictive_agent
from src.database import init_pgvector_extension, create_chat_memory_table
from src.html_formatter import format_response_as_html

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
        
        start_time = time.time()
        
        logger.info(f"Processing BOTH schedules in parallel...")
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            old_future = loop.run_in_executor(
                executor,
                vector_store_manager.create_store_from_pdf,
                session_id, old_filename, old_pdf_bytes, old_session_id
            )
            new_future = loop.run_in_executor(
                executor,
                vector_store_manager.create_store_from_pdf,
                session_id, new_filename, new_pdf_bytes, new_session_id
            )
            
            old_result, new_result = await asyncio.gather(old_future, new_future)
        
        elapsed = time.time() - start_time
        logger.info(f"OLD schedule done: {old_result.get('chunks_processed', 0)} chunks")
        logger.info(f"NEW schedule done: {new_result.get('chunks_processed', 0)} chunks")
        logger.info(f"=== UPLOAD COMPLETE ({elapsed:.1f}s) ===")
        
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
            "message": f"Both schedules processed in {elapsed:.1f}s"
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        
        is_comparison = rag_agent._is_comparison_query(query)
        logger.info(f"  Query type: {'comparison' if is_comparison else 'conversational'}")
        
        predictive_id = None
        
        if is_comparison:
            loop = asyncio.get_event_loop()
            
            context = await loop.run_in_executor(
                _query_executor,
                lambda: rag_agent._retrieve_context(query, table_names)
            )
            
            predictive_id = str(uuid.uuid4())[:8]
            _predictive_results[predictive_id] = {"status": "processing"}
            
            async def _run_predictive_background(pid, ctx, q, lang, fmt):
                try:
                    logger.info(f"  [Predictive:{pid}] Starting background analysis...")
                    pred_result = await loop.run_in_executor(
                        _query_executor,
                        lambda: predictive_agent.analyze(context=ctx, user_query=q, language=lang)
                    )
                    predictive_text = pred_result.get("predictive_insights", "")
                    if fmt == "html" and predictive_text:
                        predictive_text = format_response_as_html(predictive_text, lang)
                    _predictive_results[pid] = {
                        "status": pred_result["status"],
                        "predictive_insights": predictive_text,
                        "predictive_model": pred_result.get("model", ""),
                    }
                    logger.info(f"  [Predictive:{pid}] Complete: {len(predictive_text)} chars")
                except Exception as e:
                    logger.error(f"  [Predictive:{pid}] Failed: {e}")
                    _predictive_results[pid] = {"status": "error", "error": str(e)}
            
            asyncio.create_task(_run_predictive_background(predictive_id, context, query, language, format))
            
            logger.info(f"  Running GPT-5.2 comparison (predictive:{predictive_id} in background)...")
            
            result = await loop.run_in_executor(
                _query_executor,
                lambda: rag_agent.query(
                    user_query=query,
                    table_names=table_names,
                    session_id=vs_table,
                    language=language,
                    top_k=10,
                    preloaded_context=context
                )
            )
        else:
            result = rag_agent.query(
                user_query=query,
                table_names=table_names,
                session_id=vs_table,
                language=language,
                top_k=10
            )
        
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
        
        if predictive_id:
            response_payload["predictive_id"] = predictive_id
            response_payload["predictive_status"] = "processing"
        
        return response_payload
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query/predictive/{predictive_id}")
async def get_predictive_result(predictive_id: str):
    if predictive_id not in _predictive_results:
        raise HTTPException(status_code=404, detail="Predictive ID not found")
    
    result = _predictive_results[predictive_id]
    
    if result["status"] == "processing":
        return {"status": "processing", "predictive_id": predictive_id}
    
    response = {
        "status": result["status"],
        "predictive_id": predictive_id,
    }
    
    if result["status"] == "success":
        response["predictive_insights"] = result.get("predictive_insights", "")
        response["predictive_model"] = result.get("predictive_model", "")
    elif result["status"] == "error":
        response["error"] = result.get("error", "Unknown error")
    
    del _predictive_results[predictive_id]
    
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

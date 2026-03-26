from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
import time
import uuid
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import threading

_query_executor = ThreadPoolExecutor(max_workers=4)
_upload_progress: Dict[str, Dict[str, Any]] = {}
_predictive_progress: Dict[str, Dict[str, Any]] = {}
_progress_lock = threading.Lock()

PROGRESS_STAGES = {
    "received": {
        "step": 1,
        "total_steps": 6,
        "en": "We've received your schedule — starting the analysis now...",
        "da": "Vi har modtaget din tidsplan — starter analysen nu..."
    },
    "reading": {
        "step": 2,
        "total_steps": 6,
        "en": "Reading and scanning your document — extracting tables and data...",
        "da": "Læser og scanner dit dokument — henter tabeller og data ud..."
    },
    "extracting": {
        "step": 3,
        "total_steps": 6,
        "en": "Found your schedule data — identifying all activities...",
        "da": "Fandt dine tidsplandata — identificerer alle aktiviteter..."
    },
    "analyzing": {
        "step": 4,
        "total_steps": 6,
        "en": [
            "Nova is reading every row — detecting all delayed activities...",
            "Checking each activity against the reference date and progress...",
            "Classifying tasks — coordination, design, production, bygherre decisions...",
            "Identifying root causes and downstream consequences...",
            "Mapping delay propagation — which tasks block which disciplines...",
            "Building priority ranking — critical now vs monitor...",
            "Generating action recommendations for your project team...",
            "Assessing resource implications — manpower vs coordination bottlenecks...",
            "Writing management conclusion — almost ready...",
        ],
        "da": [
            "Nova læser hver række — finder alle forsinkede aktiviteter...",
            "Tjekker hver aktivitet mod referencedato og fremdrift...",
            "Klassificerer opgaver — koordinering, design, produktion, bygherrebeslutninger...",
            "Identificerer grundårsager og afledte konsekvenser...",
            "Kortlægger forsinkelsespropagering — hvilke opgaver blokerer hvilke discipliner...",
            "Opbygger prioriteringsrangering — kritisk nu vs overvåg...",
            "Genererer handlingsanbefalinger til dit projektteam...",
            "Vurderer ressourceimplikationer — mandskab vs koordineringsflaskehalse...",
            "Skriver ledelseskonklusion — næsten klar...",
        ]
    },
    "formatting": {
        "step": 5,
        "total_steps": 6,
        "en": "Almost there — building your report...",
        "da": "Næsten klar — opbygger din rapport..."
    },
    "complete": {
        "step": 6,
        "total_steps": 6,
        "en": "Your analysis is ready!",
        "da": "Din analyse er klar!"
    },
    "error": {
        "step": -1,
        "total_steps": 6,
        "en": "Something went wrong during the analysis. Please try again.",
        "da": "Noget gik galt under analysen. Prøv venligst igen."
    }
}


def _update_progress(analysis_id: str, stage: str, language: str = "en", detail: str = None):
    if stage not in PROGRESS_STAGES:
        return
    stage_info = PROGRESS_STAGES[stage]
    msg_value = stage_info.get(language, stage_info["en"])
    if isinstance(msg_value, list):
        with _progress_lock:
            prev = _predictive_progress.get(analysis_id)
            prev_idx = prev.get("_msg_idx", -1) if prev and prev.get("stage") == stage else -1
            next_idx = (prev_idx + 1) % len(msg_value)
            msg = msg_value[next_idx]
            _predictive_progress[analysis_id] = {
                "analysis_id": analysis_id,
                "stage": stage,
                "step": stage_info["step"],
                "total_steps": stage_info["total_steps"],
                "message": msg,
                "detail": detail,
                "timestamp": time.time(),
                "_msg_idx": next_idx,
                "_language": language
            }
    else:
        msg = msg_value
        with _progress_lock:
            _predictive_progress[analysis_id] = {
                "analysis_id": analysis_id,
                "stage": stage,
                "step": stage_info["step"],
                "total_steps": stage_info["total_steps"],
                "message": msg,
                "detail": detail,
                "timestamp": time.time(),
                "_language": language
            }

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
from src.pdf_processor import process_pdf_binary

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
            "upload": "POST /upload - Upload 2 PDF schedules for comparison agent",
            "query": "POST /query - Query the comparison AI agent",
            "predictive": "POST /predictive - Upload 2 PDFs for Nova Insight predictive analysis",
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
        
        loop = asyncio.get_event_loop()
        
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
        
        response_text = result["response"]
        
        if format == "html" and is_comparison:
            logger.info(f"Converting to HTML format...")
            response_text = format_response_as_html(response_text, language)
        elif format == "html" and not is_comparison:
            logger.info(f"Conversational response - wrapping in simple HTML...")
            response_text = f'<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; padding: 20px; color: #0f172a; line-height: 1.6; font-size: 15px;">{response_text}</div>'
        
        logger.info(f"Response generated: {len(response_text)} chars, {result['context_chunks']} chunks used")
        logger.info(f"=== QUERY COMPLETE ===")
        
        return {
            "response": response_text,
            "sources": result["sources"],
            "context_chunks": result["context_chunks"],
            "format": format
        }
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_reference_date(filename: str) -> Optional[str]:
    name = filename.replace(".pdf", "").replace(".PDF", "").strip()

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", name)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", name)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            try:
                dt = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                return dt.strftime("%d-%m-%Y")
            except ValueError:
                pass

    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", name)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", name)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    m = re.search(r"(\d{2})_(\d{2})_(\d{4})", name)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    m = re.search(r"(\d{4})_(\d{2})_(\d{2})", name)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    m = re.search(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)", name)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    return None


_GANTT_NOISE_PATTERN = re.compile(
    r'^('
    r'\d{1,2}-\d{2}$|'
    r'\d{2}-\d{2}-\d{2,4}$|'
    r'Kvt\d|'
    r'Side \d|'
    r'\d{4}$|'
    r'[A-ZÆØÅ]{1,5}\([A-ZÆØÅ0-9&;]+\)$|'
    r'[A-ZÆØÅ]{2,4}\s*-\s*[A-ZÆØÅ]{2,4}$|'
    r'[A-ZÆØÅ]{2,6}\s*\(TEGN\s*\d+\)$|'
    r'[A-ZÆØÅ]{1,5}\([A-ZÆØÅ0-9&;]+\)\s*-\s*[A-ZÆØÅ]{1,5}\([A-ZÆØÅ0-9&;]+\)$|'
    r'KL-ING$|'
    r'KL$|'
    r'Ark$|'
    r'ALJ$'
    r')',
    re.IGNORECASE
)


def _clean_gantt_noise(text: str) -> str:
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 3:
            continue
        if _GANTT_NOISE_PATTERN.match(stripped):
            continue
        if len(stripped) <= 15 and re.match(r'^[\w\s\-().;/&]+$', stripped) and not any(c.isdigit() and len(stripped) > 8 for c in stripped):
            has_letter = any(c.isalpha() for c in stripped)
            has_colon = ':' in stripped
            has_pipe = '|' in stripped
            has_at = '@' in stripped
            looks_like_task = any(kw in stripped.lower() for kw in ['uge', 'maler', 'tømrer', 'el', 'vvs', 'pap', 'flise', 'gulv', 'loft', 'tag', 'køkken', 'bad', 'fuge', 'montage', 'aflevering'])
            if has_letter and not has_colon and not has_pipe and not has_at and not looks_like_task and stripped.count(' ') <= 2:
                continue
        clean_lines.append(line)
    return "\n".join(clean_lines)


def _build_predictive_context(chunks: list[dict], filename: str) -> str:
    context_parts = []
    doc_label = f"Schedule ({filename})"

    table_chunks = [c for c in chunks if c.get("metadata", {}).get("type") == "table"]
    row_chunks = [c for c in chunks if c.get("metadata", {}).get("type") == "table_row"]
    text_chunks = [c for c in chunks if c.get("metadata", {}).get("type") == "text"]

    if row_chunks:
        context_parts.append(f"[{doc_label}] — {len(row_chunks)} data rows")
        context_parts.append("Format: ColumnHeader: value | ColumnHeader: value | ...")
        context_parts.append("IMPORTANT: The 'Id' column contains the REAL activity ID. Use that as the task identifier, NOT the row sequence number.")
        context_parts.append("")
        for chunk in row_chunks:
            context_parts.append(chunk["content"])
        context_parts.append("")
        return "\n".join(context_parts)

    if table_chunks:
        context_parts.append(f"[{doc_label}] — COMPLETE STRUCTURED TABLE DATA ({len(table_chunks)} table sections)")
        context_parts.append("")
        for chunk in table_chunks:
            content = chunk["content"]
            if "[STRUCTURED:" in content:
                content = content[:content.index("[STRUCTURED:")]
            if content.strip():
                context_parts.append(content.strip())
                context_parts.append("")
        return "\n".join(context_parts)

    if text_chunks:
        context_parts.append(f"[{doc_label}] — TEXT DATA")
        context_parts.append("")
        for chunk in text_chunks:
            content = chunk["content"]
            if content.strip():
                context_parts.append(content)
                context_parts.append("")
        if len(context_parts) <= 2:
            context_parts.append("No schedule data could be extracted.\n")
        return "\n".join(context_parts)

    context_parts.append(f"[{doc_label}]\nNo content extracted.\n")
    return "\n".join(context_parts)


@app.post("/predictive")
async def predictive_analysis(
    schedule: UploadFile = File(...),
    language: str = Form("en"),
    format: str = Form("html"),
    analysis_id: str = Form(None)
):
    start_time = time.time()

    if not analysis_id:
        analysis_id = str(uuid.uuid4())[:12]

    filename = schedule.filename or "schedule.pdf"
    filename_clean = filename.replace(".pdf", "").replace(".PDF", "")

    reference_date = _extract_reference_date(filename)

    _update_progress(analysis_id, "received", language)

    logger.info(f"=== PREDICTIVE REQUEST [{analysis_id}] ===")
    logger.info(f"Schedule: {filename} | Language: {language} | Reference date: {reference_date or 'not found in filename'}")

    if not filename.lower().endswith('.pdf'):
        _update_progress(analysis_id, "error", language)
        _schedule_progress_cleanup(analysis_id, delay=60)
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        pdf_bytes = await schedule.read()
        logger.info(f"  File read: {len(pdf_bytes)} bytes")

        _update_progress(analysis_id, "reading", language, f"{len(pdf_bytes) // 1024} KB")

        loop = asyncio.get_event_loop()

        logger.info(f"  Running OCR on PDF...")
        chunks = await loop.run_in_executor(
            _query_executor,
            lambda: process_pdf_binary(pdf_bytes, filename)
        )

        row_count = sum(1 for c in chunks if c.get("metadata", {}).get("type") == "table_row")
        table_count = sum(1 for c in chunks if c.get("metadata", {}).get("type") == "table")
        text_count = sum(1 for c in chunks if c.get("metadata", {}).get("type") == "text")
        ocr_elapsed = time.time() - start_time
        logger.info(f"  OCR complete ({ocr_elapsed:.1f}s): {len(chunks)} chunks ({row_count} rows, {table_count} tables, {text_count} text)")

        _update_progress(analysis_id, "extracting", language, f"{row_count} activities")

        context = _build_predictive_context(chunks, filename_clean)
        logger.info(f"  Context built: {len(context)} chars (all sections included)")

        _update_progress(analysis_id, "analyzing", language, f"{row_count} activities")

        logger.info(f"  Running Nova Insight predictive analysis...")
        predictive_result = await loop.run_in_executor(
            _query_executor,
            lambda: predictive_agent.analyze(
                context=context,
                user_query="Execute full two-phase analysis: detect ALL delayed activities (Phase 1) and produce decision support with root cause analysis, priority ranking, action recommendations, and resource assessment (Phase 2)",
                language=language,
                schedule_filename=filename_clean,
                reference_date=reference_date
            )
        )

        predictive_json = predictive_result.get("predictive_json", None)
        predictive_text = predictive_result.get("predictive_insights", "")
        predictive_status = predictive_result.get("status", "error")
        predictive_model = predictive_result.get("model", "")

        _update_progress(analysis_id, "formatting", language)

        if format == "html" and predictive_json:
            predictive_text = format_predictive_as_html(predictive_json, language)
        elif format == "html" and predictive_text:
            predictive_text = format_predictive_as_html(predictive_text, language)

        elapsed = time.time() - start_time
        logger.info(f"  Predictive response: {len(predictive_text)} chars, status: {predictive_status}, json={'yes' if predictive_json else 'no'}")
        logger.info(f"=== PREDICTIVE COMPLETE [{analysis_id}] ({elapsed:.1f}s) ===")

        _update_progress(analysis_id, "complete", language)

        _schedule_progress_cleanup(analysis_id)

        return {
            "analysis_id": analysis_id,
            "predictive_insights": predictive_text,
            "predictive_status": predictive_status,
            "predictive_model": predictive_model,
            "filename": filename,
            "reference_date": reference_date,
            "format": format,
            "processing_time_seconds": round(elapsed, 1)
        }

    except Exception as e:
        logger.error(f"Predictive analysis failed: {e}")
        _update_progress(analysis_id, "error", language, str(e))
        _schedule_progress_cleanup(analysis_id, delay=120)
        raise HTTPException(status_code=500, detail=str(e))


def _schedule_progress_cleanup(analysis_id: str, delay: int = 300):
    def cleanup():
        time.sleep(delay)
        with _progress_lock:
            _predictive_progress.pop(analysis_id, None)
    threading.Thread(target=cleanup, daemon=True).start()


@app.get("/predictive/progress/{analysis_id}")
async def get_predictive_progress(analysis_id: str):
    with _progress_lock:
        progress = _predictive_progress.get(analysis_id)

    if not progress:
        raise HTTPException(
            status_code=404,
            detail="No analysis found with this ID. It may have completed or expired."
        )

    if progress.get("stage") == "analyzing":
        lang = progress.get("_language", "en")
        _update_progress(analysis_id, "analyzing", lang, progress.get("detail"))
        with _progress_lock:
            progress = _predictive_progress.get(analysis_id, progress)

    resp = {k: v for k, v in progress.items() if not k.startswith("_")}
    return resp


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

"""
NUSF V2 Ingestion Routes
=========================
New FastAPI endpoints under /v2/ prefix.
These run files through the NUSF pipeline (Detect → Extract → Recognize → Normalize → Validate)
and hand the resulting compact CSV chunks to the same downstream vector store and LLM agents
used by the existing v1 routes. The v1 routes are not modified.

Endpoints:
  POST   /v2/upload                          — upload 2 schedules for comparison
  GET    /v2/upload/progress/{upload_id}     — poll upload progress
  POST   /v2/predictive                      — upload 1 schedule for Nova Insight analysis
  GET    /v2/predictive/progress/{analysis_id} — poll predictive progress
  GET    /v2/health                          — pipeline health check
  POST   /v2/inspect                         — inspect a file through the pipeline (debug)
"""
from __future__ import annotations
import asyncio
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ingestion.pipeline import IngestionPipeline, PipelineError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["v2-nusf"])

_executor = ThreadPoolExecutor(max_workers=4)
_pipeline = IngestionPipeline()

_v2_upload_progress: Dict[str, Dict[str, Any]] = {}
_v2_predictive_progress: Dict[str, Dict[str, Any]] = {}
_progress_lock = threading.Lock()

_ALLOWED_EXTENSIONS = {".pdf", ".csv"}


def _is_allowed(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in _ALLOWED_EXTENSIONS)


def _update_upload_progress(upload_id: str, **kwargs):
    with _progress_lock:
        if upload_id in _v2_upload_progress:
            _v2_upload_progress[upload_id].update(kwargs)


def _update_predictive_progress(analysis_id: str, stage: str, message: str, step: int,
                                 total_steps: int = 6, detail: str = None):
    with _progress_lock:
        _v2_predictive_progress[analysis_id] = {
            "analysis_id": analysis_id,
            "stage": stage,
            "step": step,
            "total_steps": total_steps,
            "message": message,
            "detail": detail,
            "timestamp": time.time(),
        }


def _schedule_cleanup(store: Dict, key: str, delay: int = 300):
    def _clean():
        time.sleep(delay)
        store.pop(key, None)
    threading.Thread(target=_clean, daemon=True).start()


@router.get("/health")
async def v2_health():
    from ingestion.extractors.registry import ExtractorRegistry
    return {
        "status": "healthy",
        "pipeline": "NUSF v1.0",
        "registered_extractors": ExtractorRegistry.available(),
    }


@router.post("/upload")
async def v2_upload_schedules(
    session_id: str = Form(...),
    old_session_id: str = Form(...),
    new_session_id: str = Form(...),
    old_schedule: UploadFile = File(...),
    new_schedule: UploadFile = File(...),
):
    """
    Upload two schedule files through the NUSF pipeline for comparison analysis.
    Same parameters as POST /upload — supports PDF and CSV.
    Returns upload_id for progress polling.
    """
    old_filename = old_schedule.filename or "old_schedule.pdf"
    new_filename = new_schedule.filename or "new_schedule.pdf"

    if not _is_allowed(old_filename) or not _is_allowed(new_filename):
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are accepted")

    old_bytes = await old_schedule.read()
    new_bytes = await new_schedule.read()

    upload_id = str(uuid.uuid4())[:8]

    with _progress_lock:
        _v2_upload_progress[upload_id] = {
            "status": "processing",
            "upload_id": upload_id,
            "session_id": session_id,
            "old_filename": old_filename,
            "new_filename": new_filename,
            "pipeline": "NUSF",
            "started_at": time.time(),
            "old_schedule": {"step": "queued", "detail": "Waiting to start", "progress": 0},
            "new_schedule": {"step": "queued", "detail": "Waiting to start", "progress": 0},
            "overall_progress": 0,
        }

    loop = asyncio.get_event_loop()

    async def _background():
        try:
            from src.vector_store import vector_store_manager
            from src.database import save_session_metadata

            def _process_one(file_key, filename, file_bytes, table_id):
                _update_upload_progress(
                    upload_id,
                    **{file_key: {"step": "pipeline", "detail": f"Running NUSF pipeline on {filename}...", "progress": 15}},
                )

                try:
                    schedule, chunks = _pipeline.run_from_bytes(file_bytes, filename)
                except PipelineError as e:
                    logger.error(f"[v2/upload] Pipeline error for {filename}: {e}")
                    raise

                warnings = len([i for i in schedule.validation_issues if i.level != "ERROR"])
                _update_upload_progress(
                    upload_id,
                    **{file_key: {"step": "storing", "detail": f"Storing {len(chunks)} chunks...", "progress": 60}},
                )

                result = vector_store_manager.create_store_from_chunks(
                    session_id, filename, chunks, table_id,
                    progress_callback=lambda step, detail, pct: _update_upload_progress(
                        upload_id,
                        **{file_key: {"step": step, "detail": detail, "progress": 60 + pct // 3}},
                    ),
                )

                _update_upload_progress(
                    upload_id,
                    **{file_key: {
                        "step": "complete",
                        "detail": f"{result.get('chunks_processed', 0)} chunks stored, {warnings} warnings",
                        "progress": 100,
                        "table_name": result.get("table_name"),
                        "chunks": result.get("chunks_processed", 0),
                        "nusf_activities": schedule.metadata.total_activities,
                        "nusf_quality": schedule.metadata.parse_quality_score,
                        "nusf_format": schedule.metadata.source_system,
                        "nusf_warnings": warnings,
                    }},
                )
                return result

            old_f = loop.run_in_executor(_executor, lambda: _process_one("old_schedule", old_filename, old_bytes, old_session_id))
            new_f = loop.run_in_executor(_executor, lambda: _process_one("new_schedule", new_filename, new_bytes, new_session_id))

            old_result, new_result = await asyncio.gather(old_f, new_f)
            save_session_metadata(session_id, old_filename, new_filename, old_session_id, new_session_id)

            elapsed = time.time() - _v2_upload_progress[upload_id]["started_at"]
            _update_upload_progress(
                upload_id,
                status="complete",
                overall_progress=100,
                elapsed_seconds=round(elapsed, 1),
            )
            logger.info(f"[v2/upload] Complete ({elapsed:.1f}s) upload_id={upload_id}")

        except Exception as e:
            logger.error(f"[v2/upload] Failed: {e}")
            _update_upload_progress(upload_id, status="error", error=str(e))

    asyncio.create_task(_background())

    return {
        "status": "processing",
        "upload_id": upload_id,
        "session_id": session_id,
        "pipeline": "NUSF",
        "message": f"Upload started. Poll GET /v2/upload/progress/{upload_id} for progress.",
    }


@router.get("/upload/progress/{upload_id}")
async def v2_get_upload_progress(upload_id: str):
    with _progress_lock:
        progress = _v2_upload_progress.get(upload_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    return progress


@router.post("/predictive")
async def v2_predictive_analysis(
    schedule: UploadFile = File(...),
    language: str = Form("en"),
    format: str = Form("html"),
    analysis_id: str = Form(None),
):
    """
    Upload a single schedule through the NUSF pipeline for Nova Insight predictive analysis.
    Same behaviour as POST /predictive — supports PDF and CSV.
    """
    if not analysis_id:
        analysis_id = str(uuid.uuid4())[:12]

    filename = schedule.filename or "schedule.pdf"
    filename_clean = filename.rsplit(".", 1)[0]

    if not _is_allowed(filename):
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are accepted")

    file_bytes = await schedule.read()

    _update_predictive_progress(analysis_id, "received", "Received — starting NUSF pipeline...", 1)

    import re
    from datetime import datetime

    def _extract_ref_date(name: str) -> Optional[str]:
        patterns = [
            (r"(\d{4})-(\d{2})-(\d{2})", lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
            (r"(\d{2})-(\d{2})-(\d{4})", lambda m: datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
            (r"(\d{2})\.(\d{2})\.(\d{4})", lambda m: datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
            (r"(\d{4})(\d{2})(\d{2})", lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        ]
        for pattern, parser in patterns:
            m = re.search(pattern, name)
            if m:
                try:
                    return parser(m).strftime("%d-%m-%Y")
                except ValueError:
                    continue
        return None

    reference_date = _extract_ref_date(filename_clean)

    loop = asyncio.get_event_loop()
    start_time = time.time()

    async def _background():
        try:
            _update_predictive_progress(analysis_id, "pipeline", "Running NUSF ingestion pipeline...", 2)

            try:
                schedule_obj, chunks = await loop.run_in_executor(
                    _executor,
                    lambda: _pipeline.run_from_bytes(file_bytes, filename),
                )
            except PipelineError as e:
                logger.error(f"[v2/predictive] Pipeline error: {e}")
                _update_predictive_progress(analysis_id, "error", str(e), -1)
                _schedule_cleanup(_v2_predictive_progress, analysis_id, 120)
                return

            warnings = len([i for i in schedule_obj.validation_issues if i.level != "ERROR"])
            row_count = schedule_obj.metadata.total_activities
            logger.info(
                f"[v2/predictive] Pipeline complete: {row_count} activities, "
                f"{len(chunks)} chunks, {warnings} warnings"
            )

            _update_predictive_progress(
                analysis_id, "extracting",
                f"Found {row_count} activities via NUSF ({schedule_obj.metadata.source_system})",
                3, detail=f"{row_count} activities"
            )

            from src.predictive_agent import predictive_agent
            from src.predictive_html_formatter import format_predictive_as_html

            MAX_CONTEXT_BYTES = 1_900_000
            table_chunks = [c for c in chunks if c.get("metadata", {}).get("type") == "table"]
            preamble = f"[{filename_clean}] — COMPLETE SCHEDULE DATA\nScan EVERY row for delayed activities.\n\n"
            budget = MAX_CONTEXT_BYTES - len(preamble.encode("utf-8"))
            included_parts = []
            current_bytes = 0
            for chunk in table_chunks:
                cb = len(chunk["content"].encode("utf-8")) + 1
                if current_bytes + cb > budget:
                    break
                included_parts.append(chunk["content"])
                current_bytes += cb
            context = preamble + "\n".join(included_parts) + "\n"

            _update_predictive_progress(analysis_id, "analyzing", "Nova Insight is analyzing your schedule...", 4)

            predictive_result = await loop.run_in_executor(
                _executor,
                lambda: predictive_agent.analyze(
                    context=context,
                    user_query=(
                        "Execute full two-phase analysis: detect ALL delayed activities "
                        "(Phase 1) and produce decision support with root cause analysis, "
                        "priority ranking, action recommendations, and resource assessment (Phase 2)"
                    ),
                    language=language,
                    schedule_filename=filename_clean,
                    reference_date=reference_date,
                ),
            )

            predictive_json = predictive_result.get("predictive_json")
            predictive_text = predictive_result.get("predictive_insights", "")
            predictive_status = predictive_result.get("status", "error")

            _update_predictive_progress(analysis_id, "formatting", "Building report...", 5)

            if format == "html" and predictive_json:
                predictive_text = format_predictive_as_html(predictive_json, language)
            elif format == "html" and predictive_text:
                predictive_text = format_predictive_as_html(predictive_text, language)

            elapsed = time.time() - start_time

            with _progress_lock:
                _v2_predictive_progress[analysis_id] = {
                    "analysis_id": analysis_id,
                    "stage": "complete",
                    "step": 6,
                    "total_steps": 6,
                    "message": "Analysis ready",
                    "timestamp": time.time(),
                    "result": {
                        "predictive_insights": predictive_text,
                        "predictive_status": predictive_status,
                        "filename": filename,
                        "reference_date": reference_date,
                        "format": format,
                        "processing_time_seconds": round(elapsed, 1),
                        "pipeline": "NUSF",
                        "nusf_activities": row_count,
                        "nusf_quality": schedule_obj.metadata.parse_quality_score,
                        "nusf_format": schedule_obj.metadata.source_system,
                        "nusf_warnings": warnings,
                    },
                }

            _schedule_cleanup(_v2_predictive_progress, analysis_id, 300)
            logger.info(f"[v2/predictive] Complete ({elapsed:.1f}s) analysis_id={analysis_id}")

        except Exception as e:
            logger.error(f"[v2/predictive] Unexpected error: {e}", exc_info=True)
            _update_predictive_progress(analysis_id, "error", str(e), -1)
            _schedule_cleanup(_v2_predictive_progress, analysis_id, 120)

    asyncio.create_task(_background())

    return {
        "analysis_id": analysis_id,
        "status": "processing",
        "pipeline": "NUSF",
        "message": f"Analysis started. Poll GET /v2/predictive/progress/{analysis_id} for progress.",
    }


@router.get("/predictive/progress/{analysis_id}")
async def v2_get_predictive_progress(analysis_id: str):
    with _progress_lock:
        progress = _v2_predictive_progress.get(analysis_id)
    if not progress:
        raise HTTPException(
            status_code=404,
            detail="No analysis found with this ID. It may have completed or expired.",
        )
    resp = {k: v for k, v in progress.items()}
    return resp


@router.post("/inspect")
async def v2_inspect_file(
    schedule: UploadFile = File(...),
):
    """
    Debug endpoint: run a file through the NUSF pipeline and return
    the NormalizedSchedule metadata + validation issues without
    storing anything in the vector database.
    """
    filename = schedule.filename or "schedule.pdf"
    if not _is_allowed(filename):
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are accepted")

    file_bytes = await schedule.read()
    loop = asyncio.get_event_loop()

    try:
        schedule_obj, chunks = await loop.run_in_executor(
            _executor,
            lambda: _pipeline.run_from_bytes(file_bytes, filename),
        )
    except PipelineError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": str(e),
                "issues": [i.model_dump() for i in e.issues],
            },
        )

    meta = schedule_obj.metadata
    issues = schedule_obj.validation_issues

    return {
        "pipeline": "NUSF",
        "validation_passed": schedule_obj.validation_passed,
        "filename": meta.source_filename,
        "source_system": meta.source_system,
        "total_activities": meta.total_activities,
        "total_relationships": meta.total_relationships,
        "parse_quality_score": meta.parse_quality_score,
        "parse_duration_seconds": meta.parse_duration_seconds,
        "earliest_date": meta.earliest_date.isoformat(),
        "latest_date": meta.latest_date.isoformat(),
        "duration_days": meta.duration_days,
        "compact_chunks": len(chunks),
        "validation_issues": [
            {
                "level": i.level,
                "category": i.category,
                "message": i.message,
                "remediation": i.remediation,
            }
            for i in issues
        ],
        "sample_activities": [
            {
                "source_id": a.source_id,
                "name": a.name[:80],
                "planned_start": a.planned_start.strftime("%d-%m-%Y"),
                "planned_finish": a.planned_finish.strftime("%d-%m-%Y"),
                "percent_complete": a.percent_complete,
                "activity_type": a.activity_type.value,
                "discipline": a.discipline,
            }
            for a in schedule_obj.activities[:10]
        ],
    }

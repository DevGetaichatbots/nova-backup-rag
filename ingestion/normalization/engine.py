"""
Normalization Engine
====================
Transforms raw extracted {headers, rows} into a fully typed NormalizedSchedule.
Also provides the bridge function _to_compact_csv_chunks() which converts
the NormalizedSchedule back to the semicolon-separated compact CSV format
that the existing LLM agents consume — keeping downstream agents unchanged.
"""
from __future__ import annotations
import csv
import io
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from ingestion.models.nusf import (
    Activity, ActivityType, NormalizedSchedule, Provenance,
    Relationship, ScheduleMetadata, ValidationIssue,
)
from ingestion.normalization.dates import parse_date, parse_duration_to_hours
from ingestion.normalization.mappings import FieldMapper
from ingestion.normalization.relationships import build_relationships
from ingestion.recognition.heuristics import RecognitionResult

logger = logging.getLogger(__name__)

_CSV_SEP = ";"
_MAX_CHUNK_ROWS = 250


def _serialize_row(vals: List[str]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=_CSV_SEP, quoting=csv.QUOTE_MINIMAL, lineterminator="")
    writer.writerow(vals)
    return buf.getvalue()


def _get_val(row: List[str], headers: List[str], col_name: Optional[str]) -> str:
    if not col_name:
        return ""
    try:
        idx = headers.index(col_name)
        return row[idx].strip() if idx < len(row) else ""
    except ValueError:
        return ""


def _pct_to_float(raw: str) -> float:
    if not raw:
        return 0.0
    v = raw.strip().rstrip("%").replace(",", ".")
    try:
        return min(100.0, max(0.0, float(v)))
    except ValueError:
        return 0.0


def _detect_activity_type(duration_raw: str, name: str) -> ActivityType:
    dur_lower = duration_raw.strip().lower()
    if dur_lower in ("0d", "0", ""):
        return ActivityType.MILESTONE
    name_lower = name.lower()
    if any(kw in name_lower for kw in ("summary", "phase", "opsummering", "overordnet")):
        return ActivityType.SUMMARY
    return ActivityType.TASK


class NormalizationEngine:
    """
    Converts raw extracted data into NormalizedSchedule, then bridges back
    to compact CSV for downstream LLM agents.
    """

    def normalize(
        self,
        extracted: Dict[str, Any],
        recognition: RecognitionResult,
        source_system: str,
        filename: str,
    ) -> NormalizedSchedule:
        t0 = time.time()
        headers: List[str] = extracted.get("headers", [])
        rows: List[List[str]] = extracted.get("rows", [])

        mapper = FieldMapper(source_system, recognition.column_map)

        name_col = mapper.get("name")
        start_col = mapper.get("planned_start")
        finish_col = mapper.get("planned_finish")
        dur_col = mapper.get("duration")
        pct_col = mapper.get("percent_complete")
        id_col = mapper.get("source_id")
        wbs_col = mapper.get("wbs_code")
        entydigt_col = mapper.get("entydigt_id")
        disc_col = mapper.get("discipline")
        area_col = mapper.get("area")
        floor_col = mapper.get("floor")
        pred_col = mapper.get("predecessors")
        succ_col = mapper.get("successors")
        actual_start_col = mapper.get("actual_start")
        actual_finish_col = mapper.get("actual_finish")
        act_type_col = mapper.get("activity_type")

        effective_id_col = entydigt_col or id_col

        activities: List[Activity] = []
        source_id_to_internal: Dict[str, str] = {}
        raw_predecessors: Dict[str, str] = {}
        raw_successors: Dict[str, str] = {}

        mapped_count = 0
        total_fields = len([f for f in [name_col, start_col, finish_col] if f])

        min_date: Optional[datetime] = None
        max_date: Optional[datetime] = None

        for row_idx, row in enumerate(rows):
            raw_name = _get_val(row, headers, name_col)
            raw_start = _get_val(row, headers, start_col)
            raw_finish = _get_val(row, headers, finish_col)

            if not raw_name and not raw_start and not raw_finish:
                continue

            planned_start = parse_date(raw_start)
            planned_finish = parse_date(raw_finish)

            if not planned_start and not planned_finish:
                continue

            if not planned_start:
                planned_start = planned_finish
            if not planned_finish:
                planned_finish = planned_start

            if planned_start > planned_finish:
                planned_finish = planned_start

            raw_dur = _get_val(row, headers, dur_col)
            duration_hours = parse_duration_to_hours(raw_dur)
            if duration_hours == 0 and planned_start != planned_finish:
                delta = planned_finish - planned_start
                duration_hours = max(0, int(delta.total_seconds() / 3600))

            raw_pct = _get_val(row, headers, pct_col)
            pct = _pct_to_float(raw_pct)

            raw_source_id = _get_val(row, headers, effective_id_col)
            if not raw_source_id:
                raw_source_id = str(row_idx + 1)

            raw_wbs = _get_val(row, headers, wbs_col)
            raw_disc = _get_val(row, headers, disc_col)
            raw_area = _get_val(row, headers, area_col)
            raw_floor = _get_val(row, headers, floor_col)

            if raw_floor and raw_area:
                discipline = f"{raw_floor} / {raw_area}"
            elif raw_floor:
                discipline = raw_floor
            elif raw_disc:
                discipline = raw_disc
            elif raw_area:
                discipline = raw_area
            else:
                discipline = None

            raw_act_type = _get_val(row, headers, act_type_col)
            act_type = _detect_activity_type(raw_dur, raw_name)
            if raw_act_type:
                if any(kw in raw_act_type.lower() for kw in ("milestone", "milepæl")):
                    act_type = ActivityType.MILESTONE
                elif any(kw in raw_act_type.lower() for kw in ("summary", "overordnet")):
                    act_type = ActivityType.SUMMARY

            actual_start = parse_date(_get_val(row, headers, actual_start_col)) if actual_start_col else None
            actual_finish = parse_date(_get_val(row, headers, actual_finish_col)) if actual_finish_col else None

            internal_id = str(uuid.uuid4())

            provenance: Dict[str, Provenance] = {}
            if name_col:
                provenance["name"] = Provenance(
                    source_field=name_col, source_row=row_idx,
                    is_ai_inferred=recognition.ai_needed,
                    confidence=recognition.confidence,
                )
            if start_col:
                provenance["planned_start"] = Provenance(
                    source_field=start_col, source_row=row_idx,
                    is_ai_inferred=recognition.ai_needed,
                    confidence=recognition.confidence,
                )
            if finish_col:
                provenance["planned_finish"] = Provenance(
                    source_field=finish_col, source_row=row_idx,
                    is_ai_inferred=recognition.ai_needed,
                    confidence=recognition.confidence,
                )
            if not provenance:
                provenance["_row"] = Provenance(
                    source_field=f"row_{row_idx}",
                    source_row=row_idx,
                    is_ai_inferred=False,
                    confidence=1.0,
                )

            activity = Activity(
                internal_id=internal_id,
                source_id=raw_source_id,
                name=raw_name or f"Activity {row_idx + 1}",
                wbs_code=raw_wbs or None,
                wbs_level=raw_wbs.count(".") if raw_wbs else 0,
                planned_start=planned_start,
                planned_finish=planned_finish,
                actual_start=actual_start,
                actual_finish=actual_finish,
                duration_hours=duration_hours,
                percent_complete=pct,
                activity_type=act_type,
                discipline=discipline,
                provenance=provenance,
            )

            activities.append(activity)
            source_id_to_internal[raw_source_id] = internal_id
            mapped_count += 1

            raw_pred = _get_val(row, headers, pred_col) if pred_col else ""
            raw_succ = _get_val(row, headers, succ_col) if succ_col else ""
            if raw_pred:
                raw_predecessors[internal_id] = raw_pred
            if raw_succ:
                raw_successors[internal_id] = raw_succ

            if min_date is None or planned_start < min_date:
                min_date = planned_start
            if max_date is None or planned_finish > max_date:
                max_date = planned_finish

        relationships: List[Relationship] = build_relationships(
            source_id_to_internal, raw_predecessors, raw_successors
        )

        for rel in relationships:
            if not rel.is_broken:
                for act in activities:
                    if act.internal_id == rel.successor_id:
                        if rel.predecessor_id not in act.predecessors:
                            act.predecessors.append(rel.predecessor_id)
                    if act.internal_id == rel.predecessor_id:
                        if rel.successor_id not in act.successors:
                            act.successors.append(rel.successor_id)

        now = datetime.now(tz=timezone.utc)
        min_date = min_date or now
        max_date = max_date or now
        duration_days = max(0, (max_date - min_date).days)

        quality_score = mapped_count / max(len(rows), 1)

        metadata = ScheduleMetadata(
            project_name=filename.rsplit(".", 1)[0],
            source_system=source_system,
            source_filename=filename,
            data_date=now,
            total_activities=len(activities),
            total_relationships=len(relationships),
            earliest_date=min_date,
            latest_date=max_date,
            duration_days=duration_days,
            parse_quality_score=round(min(1.0, quality_score), 4),
            parse_duration_seconds=round(time.time() - t0, 3),
        )

        schedule = NormalizedSchedule(
            metadata=metadata,
            activities=activities,
            relationships=relationships,
            validation_issues=[],
            validation_passed=True,
        )

        logger.info(
            f"[{filename}] Normalized: {len(activities)} activities, "
            f"{len(relationships)} relationships, "
            f"quality={quality_score:.2f}, "
            f"elapsed={metadata.parse_duration_seconds}s"
        )

        return schedule

    def to_compact_csv_chunks(
        self, schedule: NormalizedSchedule
    ) -> List[Dict[str, Any]]:
        """
        Bridge: converts NormalizedSchedule → compact semicolon-separated CSV chunks.
        Output format is identical to src/pdf_processor.py rows_to_compact_csv_chunks()
        so the existing vector store and LLM agents consume it unchanged.
        """
        headers = [
            "Id", "Navn", "Startdato", "Slutdato", "Varighed",
            "% Færdigt", "Fremdrift", "Foregående", "Ansvarlig",
        ]

        data_rows: List[List[str]] = []
        for act in schedule.activities:
            start_str = act.planned_start.strftime("%d-%m-%Y")
            finish_str = act.planned_finish.strftime("%d-%m-%Y")
            dur_str = f"{round(act.duration_hours / 8)}d" if act.duration_hours else "0d"
            pct_str = f"{int(act.percent_complete)}%"
            pred_str = ";".join(
                next(
                    (a.source_id for a in schedule.activities if a.internal_id == pid),
                    pid
                )
                for pid in act.predecessors
            )
            discipline = act.discipline or ""

            data_rows.append([
                act.source_id,
                act.name,
                start_str,
                finish_str,
                dur_str,
                pct_str,
                pct_str,
                pred_str,
                discipline,
            ])

        if not data_rows:
            return []

        header_line = _serialize_row(headers)
        source = schedule.metadata.source_filename
        chunks = []

        for batch_start in range(0, len(data_rows), _MAX_CHUNK_ROWS):
            batch = data_rows[batch_start: batch_start + _MAX_CHUNK_ROWS]
            lines = [_serialize_row(r) for r in batch]
            content = (
                f"FORMAT: CSV — each row = one activity. "
                f"Columns separated by semicolon (values with semicolons are quoted).\n"
                f"{header_line}\n"
                + "\n".join(lines)
            )
            part = batch_start // _MAX_CHUNK_ROWS + 1
            chunks.append({
                "content": content,
                "metadata": {
                    "type": "table",
                    "source": source,
                    "part": part,
                    "row_count": len(lines),
                },
            })

        logger.info(
            f"[{source}] Bridge: {len(schedule.activities)} activities → "
            f"{len(chunks)} compact CSV chunks"
        )
        return chunks

"""
PDF Processor - Azure Document Intelligence OCR
================================================
Extracts text and tables from PDFs, optimized for construction schedules.
Uses Azure's AI-powered document analysis for accurate OCR.
Converts OCR table output to compact CSV format (identical to CSV upload path).
"""
import csv
import io
import logging
import re
from src.azure_ocr import AzureDocumentIntelligence

logger = logging.getLogger(__name__)


def extract_from_pdf(pdf_bytes: bytes, filename: str = "document.pdf") -> dict:
    """
    Extract content from PDF using Azure Document Intelligence.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Name of the file
    
    Returns:
        Dict with 'success', 'pages', 'tables', 'raw_markdown', 'error'
    
    Raises:
        ValueError: If Azure OCR not configured
    """
    is_valid, msg = AzureDocumentIntelligence.check_credentials()
    if not is_valid:
        raise ValueError(f"Azure OCR not configured: {msg}")
    
    try:
        ocr = AzureDocumentIntelligence()
        result = ocr.extract_from_pdf(pdf_bytes, filename)
        
        if result["success"]:
            return {
                "success": True,
                "pages": result.get("pages", []),
                "tables": result.get("tables", []),
                "raw_markdown": result["raw_markdown"],
                "error": None
            }
        else:
            return {
                "success": False,
                "pages": [],
                "tables": [],
                "raw_markdown": "",
                "error": result["error"]
            }
    except Exception as e:
        logger.error(f"[{filename}] OCR extraction failed: {e}")
        raise



CSV_SEPARATOR = ";"
MAX_CHUNK_ROWS = 250
SKIP_HEADERS = {"opg", "opgavetilstand"}

KNOWN_HEADERS = {
    "id", "entydigt id", "etage", "omr.", "ansvarlig", "opgavenavn",
    "opgavetilstand", "varighed", "startdato", "slutdato",
    "% arbejde færdigt", "% færdigt", "foregående opgaver",
    "efterfølgende opgaver", "bemærkn.", "bemærkn",
    "opg.navn", "opgavenavn/aktivitet"
}

SCHEDULE_DATA_HEADERS = {
    "id", "opg", "opgavenavn", "varighed", "startdato", "slutdato",
    "% arbejde færdigt", "% færdigt", "foregående opgaver",
    "efterfølgende opgaver", "opgavetilstand", "entydigt id",
    "etage", "omr.", "ansvarlig", "bemærkn.", "bemærkn",
    "task name", "duration", "start", "finish", "start date",
    "end date", "% complete", "predecessors", "successors",
    "responsible", "area"
}

GANTT_HEADER_RE = re.compile(
    r'^(kvt\d|kvt \d|\d{4}\s*kvt|uge\s*\d|jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec|q[1-4]|'
    r'\d{4}\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec|q[1-4]|kvt)|'
    r'col\d+|\d{4}\s+\d{4})',
    re.IGNORECASE
)

MS_PROJECT_HEADERS = {
    9: ["Id", "Opgavetilstand", "Opgavenavn", "Varighed", "Startdato", "Slutdato", "% arbejde færdigt", "Foregående opgaver", "Efterfølgende opgaver"],
    10: ["Id", "Opgavetilstand", "Opgavenavn", "Varighed", "Startdato", "Slutdato", "% arbejde færdigt", "Foregående opgaver", "Efterfølgende opgaver", "Col10"],
    11: ["Id", "Opgavetilstand", "Opgavenavn", "Varighed", "Startdato", "Slutdato", "% arbejde færdigt", "Foregående opgaver", "Efterfølgende opgaver", "Col10", "Col11"],
}


def _is_schedule_column(header: str) -> bool:
    h = header.strip().lower()
    if not h:
        return False
    if h in SCHEDULE_DATA_HEADERS:
        return True
    if GANTT_HEADER_RE.match(h):
        return False
    if h.startswith("col") and h[3:].isdigit():
        return False
    return True


def _serialize_compact_row(vals: list[str], sep: str = CSV_SEPARATOR) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=sep, quoting=csv.QUOTE_MINIMAL, lineterminator="")
    writer.writerow(vals)
    return buf.getvalue()


def _header_score(row_vals):
    if not row_vals:
        return 0
    cleaned = [str(v).strip().lower() for v in row_vals if str(v).strip()]
    return sum(1 for v in cleaned if v in KNOWN_HEADERS or any(kh in v for kh in KNOWN_HEADERS))


def _detect_header_row(rows, col_count):
    if not rows:
        return [], rows

    raw_header = rows[0]
    header_row = raw_header
    best_score = _header_score(raw_header)
    best_header_idx = 0

    for check_idx in range(1, min(5, len(rows))):
        score = _header_score(rows[check_idx])
        if score > best_score:
            best_score = score
            header_row = rows[check_idx]
            best_header_idx = check_idx

    MIN_HEADER_SCORE = 3

    if best_header_idx > 0 and best_score >= MIN_HEADER_SCORE:
        data_rows = [r for i, r in enumerate(rows) if i != best_header_idx and i != 0]
        return header_row, data_rows
    elif best_score >= MIN_HEADER_SCORE:
        return header_row, rows[1:]
    else:
        fallback = MS_PROJECT_HEADERS.get(col_count)
        if not fallback:
            closest = min(MS_PROJECT_HEADERS.keys(), key=lambda k: abs(k - col_count))
            fb = MS_PROJECT_HEADERS[closest]
            if col_count > closest:
                fallback = fb + [f"Col{i+1}" for i in range(closest, col_count)]
            else:
                fallback = fb[:col_count]

        skip_rows = set()
        for ri in range(min(5, len(rows))):
            row_vals = [str(v).strip().lower() for v in rows[ri] if str(v).strip()]
            is_data = any(v.isdigit() for v in row_vals)
            if not is_data and row_vals:
                skip_rows.add(ri)

        data_rows = [r for i, r in enumerate(rows) if i not in skip_rows]
        return fallback, data_rows


def rows_to_compact_csv_chunks(headers: list[str], data_rows: list[list[str]], source: str) -> list[dict]:
    if not headers or not data_rows:
        return []

    display_headers = [h for h in headers if h.lower() not in SKIP_HEADERS]
    keep_indices = [i for i, h in enumerate(headers) if h.lower() not in SKIP_HEADERS]

    header_line = _serialize_compact_row(display_headers)

    chunks = []
    total_stored = 0
    for batch_start in range(0, len(data_rows), MAX_CHUNK_ROWS):
        batch = data_rows[batch_start:batch_start + MAX_CHUNK_ROWS]
        compact_lines = []
        for row in batch:
            vals = [row[idx].strip() if idx < len(row) else "" for idx in keep_indices]
            compact_lines.append(_serialize_compact_row(vals))

        if compact_lines:
            content = f"FORMAT: CSV — each row = one activity. Columns separated by semicolon (values with semicolons are quoted).\n{header_line}\n" + "\n".join(compact_lines)
            part_num = batch_start // MAX_CHUNK_ROWS + 1
            total_stored += len(compact_lines)
            chunks.append({
                "content": content,
                "metadata": {
                    "type": "table",
                    "source": source,
                    "part": part_num,
                    "row_count": len(compact_lines)
                }
            })

    logger.info(f"  [{source}] Compact CSV: {len(chunks)} chunks, {total_stored}/{len(data_rows)} rows, {len(display_headers)} columns")
    return chunks


def _filter_schedule_columns(headers: list[str], rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    sched_indices = [i for i, h in enumerate(headers) if _is_schedule_column(h)]
    if not sched_indices:
        sched_indices = list(range(len(headers)))

    filtered_h = [headers[i] for i in sched_indices]
    filtered_rows = []
    for row in rows:
        vals = [row[i] if i < len(row) else "" for i in sched_indices]
        filtered_rows.append(vals)
    return filtered_h, filtered_rows


def _ocr_tables_to_compact_csv_chunks(tables: list[dict], filename: str) -> list[dict]:
    canonical_headers = []
    all_data_rows = []

    for table in tables:
        table_id = table.get("table_id", 0)
        col_count = table.get("column_count", 0)
        rows = table.get("rows", [])

        if not rows:
            continue

        header_row, data_rows = _detect_header_row(rows, col_count)
        header_clean = [str(h).strip() for h in header_row]

        sched_headers, sched_data = _filter_schedule_columns(header_clean, data_rows)

        logger.info(f"[{filename}] Table {table_id}: {len(sched_data)} data rows, "
                     f"schedule cols={len(sched_headers)}/{len(header_clean)} "
                     f"(score={_header_score(header_row)}): {sched_headers}")

        if sched_data:
            sample = sched_data[0]
            sample_mapped = " | ".join(
                f"{sched_headers[i] if i < len(sched_headers) else f'Col{i}'}: {str(sample[i]).strip()[:30]}"
                for i in range(min(len(sample), len(sched_headers)))
            )
            logger.info(f"[{filename}] Table {table_id} first data row: {sample_mapped}")

        if not canonical_headers:
            canonical_headers = sched_headers
        else:
            canon_low = [h.lower().strip() for h in canonical_headers]
            table_low = [h.lower().strip() for h in sched_headers]

            if table_low == canon_low:
                pass
            else:
                col_map = {}
                for ci, ch in enumerate(canon_low):
                    for fi, fh in enumerate(table_low):
                        if fh == ch:
                            col_map[ci] = fi
                            break
                min_required = max(1, int(0.6 * len(canonical_headers)))
                if len(col_map) < min_required:
                    logger.info(f"[{filename}] Table {table_id}: schedule headers don't match canonical "
                                f"(matched {len(col_map)}/{len(canonical_headers)}, need {min_required}), skipping")
                    continue
                remapped = []
                for row in sched_data:
                    new_row = [row[col_map[ci]] if ci in col_map and col_map[ci] < len(row) else "" for ci in range(len(canonical_headers))]
                    remapped.append(new_row)
                sched_data = remapped
                logger.info(f"[{filename}] Table {table_id}: remapped {len(col_map)}/{len(canonical_headers)} columns")

        for row in sched_data:
            cleaned = [str(v).strip() if v else "" for v in row]
            if any(v for v in cleaned):
                while len(cleaned) < len(canonical_headers):
                    cleaned.append("")
                all_data_rows.append(cleaned[:len(canonical_headers)])

    if not canonical_headers or not all_data_rows:
        logger.warning(f"[{filename}] No structured table data found in OCR output")
        return []

    logger.info(f"[{filename}] OCR total: {len(all_data_rows)} schedule rows from {len(tables)} tables")
    return rows_to_compact_csv_chunks(canonical_headers, all_data_rows, filename)


def _parse_raw_markdown_tables(raw_markdown: str, filename: str) -> tuple[list[str], list[list[str]]]:
    tables_html = re.findall(r'<table>.*?</table>', raw_markdown, re.DOTALL)
    if not tables_html:
        return [], []

    logger.info(f"[{filename}] Raw markdown: found {len(tables_html)} HTML tables")

    canonical_headers = []
    all_data_rows = []

    for ti, table_html in enumerate(tables_html):
        header_matches = list(re.finditer(r'<tr>\s*((?:<th[^>]*>.*?</th>\s*)+)</tr>', table_html, re.DOTALL))
        if not header_matches:
            continue

        header_tr = header_matches[0].group(1)
        raw_headers = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<th[^>]*>(.*?)</th>', header_tr, re.DOTALL)]

        sched_indices = [i for i, h in enumerate(raw_headers) if _is_schedule_column(h)]
        if not sched_indices:
            sched_indices = list(range(len(raw_headers)))

        filtered_h = [raw_headers[i] for i in sched_indices]

        if _header_score(filtered_h) < 2:
            continue

        if not canonical_headers:
            canonical_headers = filtered_h
            col_indices_map = list(range(len(sched_indices)))
            logger.info(f"[{filename}] Raw MD table {ti}: canonical headers ({len(canonical_headers)}): {canonical_headers}")
        else:
            canon_low = [h.lower().strip() for h in canonical_headers]
            table_low = [h.lower().strip() for h in filtered_h]
            col_indices_map = []
            matched = 0
            for ci, ch in enumerate(canon_low):
                found = -1
                for fi, fh in enumerate(table_low):
                    if fh == ch:
                        found = fi
                        matched += 1
                        break
                col_indices_map.append(found)
            min_required = max(1, int(0.6 * len(canonical_headers)))
            if matched < min_required:
                continue

        for row_match in re.finditer(r'<tr>\s*((?:<td[^>]*>.*?</td>\s*)+)</tr>', table_html, re.DOTALL):
            raw_cells = re.findall(r'<td[^>]*>(.*?)</td>', row_match.group(1), re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in raw_cells]

            row_vals = []
            for mi, ci in enumerate(col_indices_map):
                if ci < 0 or ci >= len(sched_indices):
                    row_vals.append("")
                else:
                    src_idx = sched_indices[ci]
                    row_vals.append(cells[src_idx] if 0 <= src_idx < len(cells) else "")

            if any(v.strip() for v in row_vals):
                all_data_rows.append(row_vals)

    logger.info(f"[{filename}] Raw markdown parsed: {len(canonical_headers)} columns, {len(all_data_rows)} rows")
    return canonical_headers, all_data_rows


def process_pdf_binary(pdf_bytes: bytes, filename: str = "document.pdf") -> list[dict]:
    """
    Process PDF binary to compact CSV chunks (same format as CSV upload path).

    OCR extracts tables, then converts to semicolon-separated CSV chunks
    with 250 rows each, type="table", ready for zero-vector storage.
    Uses structured tables first; falls back to raw_markdown HTML parsing
    if structured tables yield no data.

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Name of the file

    Returns:
        List of chunk dicts with 'content' and 'metadata' (type="table")

    Raises:
        ValueError: If Azure OCR not configured or extraction fails
    """
    extraction = extract_from_pdf(pdf_bytes, filename)

    if not extraction["success"]:
        raise ValueError(f"PDF extraction failed: {extraction['error']}")

    tables = extraction.get("tables", [])
    logger.info(f"[{filename}] OCR extracted {len(tables)} tables")

    chunks = _ocr_tables_to_compact_csv_chunks(tables, filename)

    if not chunks:
        raw_markdown = extraction.get("raw_markdown", "")
        if raw_markdown:
            logger.info(f"[{filename}] Structured tables failed — trying raw markdown HTML parsing")
            headers, data_rows = _parse_raw_markdown_tables(raw_markdown, filename)
            if headers and data_rows:
                chunks = rows_to_compact_csv_chunks(headers, data_rows, filename)

    if not chunks:
        logger.warning(f"[{filename}] No schedule data could be extracted from OCR output")

    logger.info(f"[{filename}] Final: {len(chunks)} compact CSV chunks")
    return chunks

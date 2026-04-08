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

MS_PROJECT_HEADERS = {
    9: ["Id", "Opgavetilstand", "Opgavenavn", "Varighed", "Startdato", "Slutdato", "% arbejde færdigt", "Foregående opgaver", "Efterfølgende opgaver"],
    10: ["Id", "Opgavetilstand", "Opgavenavn", "Varighed", "Startdato", "Slutdato", "% arbejde færdigt", "Foregående opgaver", "Efterfølgende opgaver", "Col10"],
    11: ["Id", "Opgavetilstand", "Opgavenavn", "Varighed", "Startdato", "Slutdato", "% arbejde færdigt", "Foregående opgaver", "Efterfølgende opgaver", "Col10", "Col11"],
}


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


def _ocr_tables_to_compact_csv_chunks(tables: list[dict], filename: str) -> list[dict]:
    all_headers = []
    all_data_rows = []

    for table in tables:
        table_id = table.get("table_id", 0)
        col_count = table.get("column_count", 0)
        rows = table.get("rows", [])

        if not rows:
            continue

        header_row, data_rows = _detect_header_row(rows, col_count)

        header_clean = [str(h).strip() for h in header_row]
        logger.info(f"[{filename}] Table {table_id}: {len(data_rows)} data rows, headers (score={_header_score(header_row)}): {header_clean}")

        if data_rows:
            sample = data_rows[0]
            sample_mapped = " | ".join(
                f"{header_clean[i] if i < len(header_clean) else f'Col{i}'}: {str(sample[i]).strip()[:30]}"
                for i in range(min(len(sample), len(header_clean)))
            )
            logger.info(f"[{filename}] Table {table_id} first data row: {sample_mapped}")

        if not all_headers:
            all_headers = header_clean
        else:
            if header_clean != all_headers:
                col_map = {}
                for ci, ch in enumerate(all_headers):
                    ch_low = ch.lower().strip()
                    for fi, fh in enumerate(header_clean):
                        if fh.lower().strip() == ch_low:
                            col_map[ci] = fi
                            break
                if len(col_map) < len(all_headers) - 1:
                    logger.info(f"[{filename}] Table {table_id}: headers don't match canonical, skipping")
                    continue
                remapped_rows = []
                for row in data_rows:
                    new_row = []
                    for ci in range(len(all_headers)):
                        src_idx = col_map.get(ci, -1)
                        new_row.append(row[src_idx] if 0 <= src_idx < len(row) else "")
                    remapped_rows.append(new_row)
                data_rows = remapped_rows
                logger.info(f"[{filename}] Table {table_id}: remapped {len(col_map)}/{len(all_headers)} columns")

        for row in data_rows:
            cleaned = [str(v).strip() if v else "" for v in row]
            if any(v for v in cleaned):
                while len(cleaned) < len(all_headers):
                    cleaned.append("")
                all_data_rows.append(cleaned[:len(all_headers)])

    if not all_headers or not all_data_rows:
        logger.warning(f"[{filename}] No structured table data found in OCR output")
        return []

    display_headers = [h for h in all_headers if h.lower() not in SKIP_HEADERS]
    keep_indices = [i for i, h in enumerate(all_headers) if h.lower() not in SKIP_HEADERS]

    header_line = _serialize_compact_row(display_headers)

    chunks = []
    total_stored = 0
    for batch_start in range(0, len(all_data_rows), MAX_CHUNK_ROWS):
        batch = all_data_rows[batch_start:batch_start + MAX_CHUNK_ROWS]
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
                    "source": filename,
                    "part": part_num,
                    "row_count": len(compact_lines)
                }
            })

    logger.info(f"[{filename}] OCR → compact CSV: {len(chunks)} chunks, {total_stored}/{len(all_data_rows)} rows stored, {len(display_headers)} columns")
    return chunks


def process_pdf_binary(pdf_bytes: bytes, filename: str = "document.pdf") -> list[dict]:
    """
    Process PDF binary to compact CSV chunks (same format as CSV upload path).

    OCR extracts tables, then converts to semicolon-separated CSV chunks
    with 250 rows each, type="table", ready for zero-vector storage.

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
        if raw_markdown and raw_markdown.strip():
            logger.warning(f"[{filename}] No structured tables found in OCR output — attempting raw markdown conversion")
            lines = raw_markdown.strip().split("\n")
            data_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
            if data_lines:
                content = f"FORMAT: CSV — each row = one activity. Columns separated by semicolon (values with semicolons are quoted).\nRawData\n" + "\n".join(data_lines[:MAX_CHUNK_ROWS])
                chunks.append({
                    "content": content,
                    "metadata": {
                        "type": "table",
                        "source": filename,
                        "part": 1,
                        "row_count": len(data_lines[:MAX_CHUNK_ROWS]),
                        "fallback": "raw_markdown"
                    }
                })

    logger.info(f"[{filename}] Final: {len(chunks)} compact CSV chunks")
    return chunks

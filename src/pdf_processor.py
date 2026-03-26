"""
PDF Processor - Azure Document Intelligence OCR
================================================
Extracts text and tables from PDFs, optimized for construction schedules.
Uses Azure's AI-powered document analysis for accurate OCR.
Preserves table structure using Azure's structured table output.
"""
import json
import logging
from src.azure_ocr import AzureDocumentIntelligence
from src.embeddings import count_tokens, MAX_TOKENS

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


def table_to_markdown(table: dict) -> str:
    """Convert structured table to markdown format."""
    rows = table.get("rows", [])
    if not rows:
        return ""
    
    lines = []
    for i, row in enumerate(rows):
        line = "| " + " | ".join(str(cell) for cell in row) + " |"
        lines.append(line)
        if i == 0:
            separator = "| " + " | ".join("---" for _ in row) + " |"
            lines.append(separator)
    
    return "\n".join(lines)


def chunk_text_content(content: str, chunk_size: int = 1000) -> list[str]:
    """Split text into chunks by paragraphs."""
    if not content or not content.strip():
        return []
    
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            if len(para) <= chunk_size:
                current_chunk = para
            else:
                words = para.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= chunk_size:
                        current_chunk += (" " if current_chunk else "") + word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def process_pdf_binary(pdf_bytes: bytes, filename: str = "document.pdf",
                       chunk_size: int = 1000, chunk_overlap: int = 100) -> list[dict]:
    """
    Process PDF binary to chunks ready for embedding.
    
    Tables are chunked separately to preserve structure.
    Each table row becomes a searchable chunk with full table context.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Name of the file
        chunk_size: Max chars per text chunk (tables handled separately)
        chunk_overlap: Overlap for text chunks
    
    Returns:
        List of chunk dicts with 'content' and 'metadata'
    
    Raises:
        ValueError: If Azure OCR not configured or extraction fails
    """
    extraction = extract_from_pdf(pdf_bytes, filename)
    
    if not extraction["success"]:
        raise ValueError(f"PDF extraction failed: {extraction['error']}")
    
    chunks = []
    chunk_index = 0

    raw_markdown = extraction.get("raw_markdown", "")
    if raw_markdown and raw_markdown.strip():
        chunks.append({
            "content": raw_markdown.strip(),
            "metadata": {
                "chunk_index": chunk_index,
                "filename": filename,
                "type": "raw_markdown",
                "source": "azure_ocr"
            }
        })
        chunk_index += 1
        logger.info(f"[{filename}] Raw markdown chunk: {len(raw_markdown)} chars")
    
    tables = extraction.get("tables", [])
    for table in tables:
        table_id = table.get("table_id", 0)
        row_count = table.get("row_count", 0)
        col_count = table.get("column_count", 0)
        page_numbers = table.get("page_numbers", [1])
        rows = table.get("rows", [])
        cells = table.get("cells", [])
        has_merged_cells = table.get("has_merged_cells", False)
        
        if not rows:
            continue
        
        raw_header = rows[0] if rows else []
        
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
        
        def _header_score(row_vals):
            if not row_vals:
                return 0
            cleaned = [str(v).strip().lower() for v in row_vals if str(v).strip()]
            return sum(1 for v in cleaned if v in KNOWN_HEADERS or any(kh in v for kh in KNOWN_HEADERS))
        
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
            logger.info(f"[{filename}] Table {table_id}: Header found at row {best_header_idx} (score={best_score}), not row 0")
            rows = [header_row] + [r for i, r in enumerate(rows) if i != best_header_idx and i != 0]
        elif best_score < MIN_HEADER_SCORE:
            logger.warning(f"[{filename}] Table {table_id}: Header detection FAILED (best_score={best_score} < {MIN_HEADER_SCORE}). Using MS Project fallback for {col_count} columns...")

            fallback = MS_PROJECT_HEADERS.get(col_count)
            if not fallback:
                closest = min(MS_PROJECT_HEADERS.keys(), key=lambda k: abs(k - col_count))
                fb = MS_PROJECT_HEADERS[closest]
                if col_count > closest:
                    fallback = fb + [f"Col{i+1}" for i in range(closest, col_count)]
                else:
                    fallback = fb[:col_count]

            header_row = fallback
            logger.info(f"[{filename}] Table {table_id}: Using fallback headers: {header_row}")

            skip_rows = set()
            for ri in range(min(5, len(rows))):
                row_vals = [str(v).strip().lower() for v in rows[ri] if str(v).strip()]
                is_data = False
                for v in row_vals:
                    if v.isdigit():
                        is_data = True
                        break
                if not is_data and row_vals:
                    skip_rows.add(ri)
            if skip_rows:
                logger.info(f"[{filename}] Table {table_id}: Skipping non-data rows at indices {skip_rows}")

            rows = [r for i, r in enumerate(rows) if i not in skip_rows]
        
        logger.info(f"[{filename}] Table {table_id} headers (score={best_score}): {[str(h).strip() for h in header_row]}")
        if rows:
            sample_row = rows[0]
            sample_mapped = " | ".join(f"{header_row[i] if i < len(header_row) else f'Col{i}'}: {str(sample_row[i]).strip()[:30]}" for i in range(min(len(sample_row), len(header_row))))
            logger.info(f"[{filename}] Table {table_id} first data row: {sample_mapped}")
        
        MAX_TABLE_CHUNK_CHARS = 120000

        corrected_rows = [header_row] + rows
        corrected_table = {**table, "rows": corrected_rows}
        table_md = table_to_markdown(corrected_table)
        structured_json = json.dumps({"table_id": table_id, "rows": rows, "cells": cells, "pages": page_numbers})
        
        full_table_content = f"TABLE {table_id} (Pages {page_numbers})\n{table_md}\n[STRUCTURED: {structured_json}]"
        
        if len(full_table_content) <= MAX_TABLE_CHUNK_CHARS:
            chunks.append({
                "content": full_table_content,
                "metadata": {
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "type": "table",
                    "table_id": table_id,
                    "row_count": row_count,
                    "column_count": col_count,
                    "page_numbers": page_numbers,
                    "has_merged_cells": has_merged_cells,
                    "source": "azure_ocr"
                }
            })
            chunk_index += 1
        else:
            table_content_no_json = f"TABLE {table_id} (Pages {page_numbers})\n{table_md}"
            
            if len(table_content_no_json) <= MAX_TABLE_CHUNK_CHARS:
                chunks.append({
                    "content": table_content_no_json,
                    "metadata": {
                        "chunk_index": chunk_index,
                        "filename": filename,
                        "type": "table",
                        "table_id": table_id,
                        "row_count": row_count,
                        "column_count": col_count,
                        "page_numbers": page_numbers,
                        "has_merged_cells": has_merged_cells,
                        "source": "azure_ocr"
                    }
                })
                chunk_index += 1
            else:
                md_lines = table_md.split("\n")
                current_part = f"TABLE {table_id} (Pages {page_numbers})\n"
                part_num = 1
                
                for line in md_lines:
                    if len(current_part) + len(line) + 1 > MAX_TABLE_CHUNK_CHARS:
                        if current_part.strip():
                            chunks.append({
                                "content": current_part,
                                "metadata": {
                                    "chunk_index": chunk_index,
                                    "filename": filename,
                                    "type": "table",
                                    "table_id": table_id,
                                    "part": part_num,
                                    "row_count": row_count,
                                    "column_count": col_count,
                                    "page_numbers": page_numbers,
                                    "source": "azure_ocr"
                                }
                            })
                            chunk_index += 1
                            part_num += 1
                        current_part = f"TABLE {table_id} Part {part_num} (Pages {page_numbers})\n"
                    current_part += line + "\n"
                
                if current_part.strip():
                    chunks.append({
                        "content": current_part,
                        "metadata": {
                            "chunk_index": chunk_index,
                            "filename": filename,
                            "type": "table",
                            "table_id": table_id,
                            "part": part_num,
                            "row_count": row_count,
                            "column_count": col_count,
                            "page_numbers": page_numbers,
                            "source": "azure_ocr"
                        }
                    })
                    chunk_index += 1
            
            logger.info(f"[{filename}] Large table {table_id} split into {part_num if 'part_num' in dir() else 1} chunks (was {len(full_table_content)} chars)")
        
        for row_idx, row in enumerate(rows[1:], start=1):
            row_cells = [c for c in cells if c.get("row") == row_idx]
            
            row_page = page_numbers[0] if page_numbers else 1
            for cell in row_cells:
                if "bounding_regions" in cell:
                    for br in cell.get("bounding_regions", []):
                        row_page = br.get("pageNumber", row_page)
                        break
            
            row_content_parts = []
            has_any_value = False
            for i, cell_val in enumerate(row):
                header = header_row[i] if i < len(header_row) else f"Col{i+1}"
                val = str(cell_val).strip() if cell_val else ""
                row_content_parts.append(f"{header}: {val}")
                if val:
                    has_any_value = True
            
            if has_any_value:
                row_content = " | ".join(row_content_parts)
                chunks.append({
                    "content": row_content,
                    "metadata": {
                        "chunk_index": chunk_index,
                        "filename": filename,
                        "type": "table_row",
                        "table_id": table_id,
                        "row_index": row_idx,
                        "page_number": row_page,
                        "cells_data": json.dumps(row_cells) if row_cells else None,
                        "source": "azure_ocr"
                    }
                })
                chunk_index += 1
    
    pages = extraction.get("pages", [])
    for page in pages:
        page_content = page.get("content", "")
        page_number = page.get("page_number", 1)
        total_pages = page.get("total_pages", 1)
        
        text_chunks = chunk_text_content(page_content, chunk_size)
        
        for i, text in enumerate(text_chunks):
            chunks.append({
                "content": text,
                "metadata": {
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "type": "text",
                    "page_number": page_number,
                    "total_pages": total_pages,
                    "page_chunk_index": i,
                    "source": "azure_ocr"
                }
            })
            chunk_index += 1
    
    if not chunks and extraction["raw_markdown"]:
        text_chunks = chunk_text_content(extraction["raw_markdown"], chunk_size)
        for i, text in enumerate(text_chunks):
            chunks.append({
                "content": text,
                "metadata": {
                    "chunk_index": i,
                    "filename": filename,
                    "type": "text",
                    "source": "azure_ocr"
                }
            })
    
    safe_token_limit = MAX_TOKENS - 100
    final_chunks = []
    split_count = 0
    for chunk in chunks:
        token_count = count_tokens(chunk["content"])
        if token_count <= safe_token_limit:
            final_chunks.append(chunk)
        else:
            from src.embeddings import split_oversized_text
            parts = split_oversized_text(chunk["content"], safe_token_limit)
            split_count += 1
            for part_idx, part_text in enumerate(parts):
                new_chunk = {
                    "content": part_text,
                    "metadata": {**chunk["metadata"], "chunk_index": len(final_chunks), "split_part": part_idx + 1, "split_total": len(parts)}
                }
                final_chunks.append(new_chunk)

    if split_count > 0:
        logger.info(f"[{filename}] Token safety: split {split_count} oversized chunks → {len(final_chunks)} total (was {len(chunks)})")
    
    logger.info(f"[{filename}] Created {len(final_chunks)} chunks ({len(tables)} tables, {len(pages)} pages)")
    
    return final_chunks

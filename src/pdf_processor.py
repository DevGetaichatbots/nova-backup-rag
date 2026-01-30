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
        
        header_row = rows[0] if rows else []
        
        structured_table = {
            "table_id": table_id,
            "rows": rows,
            "cells": cells,
            "pages": page_numbers
        }
        table_content = f"TABLE {table_id} (Pages {page_numbers})\n"
        table_content += table_to_markdown(table)
        table_content += f"\n[STRUCTURED: {json.dumps(structured_table)}]"
        
        chunks.append({
            "content": table_content,
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
        
        for row_idx, row in enumerate(rows[1:], start=1):
            row_cells = [c for c in cells if c.get("row") == row_idx]
            
            row_page = page_numbers[0] if page_numbers else 1
            for cell in row_cells:
                if "bounding_regions" in cell:
                    for br in cell.get("bounding_regions", []):
                        row_page = br.get("pageNumber", row_page)
                        break
            
            row_content_parts = []
            for i, cell_val in enumerate(row):
                if cell_val:
                    header = header_row[i] if i < len(header_row) else f"Col{i+1}"
                    row_content_parts.append(f"{header}: {cell_val}")
            
            if row_content_parts:
                row_content = f"Row {row_idx} (Page {row_page}): " + " | ".join(row_content_parts)
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
    
    logger.info(f"[{filename}] Created {len(chunks)} chunks ({len(tables)} tables, {len(pages)} pages)")
    
    return chunks

import io
import tempfile
import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> list[dict]:
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    
    pages = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({
                "content": text,
                "page_number": page_num + 1,
                "total_pages": len(reader.pages)
            })
    
    return pages


def chunk_documents(pages: list[dict], chunk_size: int = 1000, chunk_overlap: int = 100) -> list[dict]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = []
    for page in pages:
        page_chunks = text_splitter.split_text(page["content"])
        for i, chunk_content in enumerate(page_chunks):
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "page_number": page["page_number"],
                    "total_pages": page["total_pages"],
                    "chunk_index": i
                }
            })
    
    return chunks


def process_pdf_binary(pdf_bytes: bytes, chunk_size: int = 1000, chunk_overlap: int = 100) -> list[dict]:
    pages = extract_text_from_pdf_bytes(pdf_bytes)
    chunks = chunk_documents(pages, chunk_size, chunk_overlap)
    return chunks

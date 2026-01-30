"""
PDF Processor using Azure Document Intelligence OCR
====================================================
Extracts text and tables from PDFs using Azure's AI-powered document analysis.
Falls back to pypdf if Azure OCR fails or credentials are not configured.
"""
import io
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

AzureDocumentIntelligence = None
PdfReader = None
AZURE_OCR_AVAILABLE = False
PYPDF_AVAILABLE = False

try:
    from src.azure_ocr import AzureDocumentIntelligence
    AZURE_OCR_AVAILABLE = True
except (ImportError, ValueError) as e:
    logger.warning(f"Azure OCR not available, will try pypdf fallback: {e}")

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    pass


def extract_text_with_azure_ocr(pdf_bytes: bytes, filename: str = "document.pdf") -> list[dict]:
    """
    Extract text from PDF using Azure Document Intelligence OCR.
    Returns list of page-like dicts with content for chunking.
    """
    if not AZURE_OCR_AVAILABLE or AzureDocumentIntelligence is None:
        logger.warning(f"[{filename}] Azure OCR not available")
        return []
    
    is_valid, msg = AzureDocumentIntelligence.check_credentials()
    if not is_valid:
        logger.warning(f"[{filename}] Azure OCR credentials not configured: {msg}")
        return []
    
    try:
        ocr = AzureDocumentIntelligence()
        pages = ocr.extract_pages_from_pdf(pdf_bytes, filename)
        
        if pages:
            logger.info(f"[{filename}] Azure OCR extracted {len(pages)} pages")
            return [
                {
                    "content": page["content"],
                    "page_number": page["page_number"],
                    "total_pages": page["total_pages"],
                    "source": "azure_ocr"
                }
                for page in pages
            ]
        else:
            logger.error(f"[{filename}] Azure OCR returned no pages")
            return []
    except Exception as e:
        logger.error(f"[{filename}] Azure OCR exception: {e}")
        return []


def extract_text_with_pypdf(pdf_bytes: bytes) -> list[dict]:
    """
    Fallback: Extract text from PDF using pypdf.
    """
    if not PYPDF_AVAILABLE:
        logger.error("pypdf not available for fallback")
        return []
    
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        pages = []
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({
                    "content": text,
                    "page_number": page_num + 1,
                    "total_pages": len(reader.pages),
                    "source": "pypdf"
                })
        
        return pages
    except Exception as e:
        logger.error(f"pypdf extraction failed: {e}")
        return []


def extract_text_from_pdf_bytes(pdf_bytes: bytes, filename: str = "document.pdf") -> list[dict]:
    """
    Extract text from PDF bytes.
    Uses Azure Document Intelligence OCR if available, falls back to pypdf.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Name of the file (for logging)
    
    Returns:
        List of dicts with 'content', 'page_number', 'total_pages', 'source'
    """
    pages = []
    
    if AZURE_OCR_AVAILABLE:
        try:
            pages = extract_text_with_azure_ocr(pdf_bytes, filename)
            if pages:
                logger.info(f"[{filename}] Using Azure OCR extraction")
                return pages
        except Exception as e:
            logger.warning(f"[{filename}] Azure OCR failed, trying pypdf: {e}")
    
    if not pages and PYPDF_AVAILABLE:
        logger.info(f"[{filename}] Using pypdf fallback extraction")
        pages = extract_text_with_pypdf(pdf_bytes)
    
    if not pages:
        logger.error(f"[{filename}] No extraction method succeeded")
    
    return pages


def chunk_documents(pages: list[dict], chunk_size: int = 1000, chunk_overlap: int = 100) -> list[dict]:
    """
    Split extracted pages into smaller chunks for embedding.
    
    Args:
        pages: List of page dicts from extract_text_from_pdf_bytes
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunk dicts with 'content' and 'metadata'
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = []
    for page in pages:
        page_chunks = text_splitter.split_text(page["content"])
        for i, chunk_content in enumerate(page_chunks):
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "page_number": page.get("page_number", 1),
                    "total_pages": page.get("total_pages", 1),
                    "chunk_index": i,
                    "source": page.get("source", "unknown")
                }
            })
    
    return chunks


def process_pdf_binary(pdf_bytes: bytes, filename: str = "document.pdf",
                       chunk_size: int = 1000, chunk_overlap: int = 100) -> list[dict]:
    """
    Main function: Process PDF binary to chunks ready for embedding.
    
    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Name of the file (for logging and metadata)
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunk dicts with 'content' and 'metadata' ready for embedding
    """
    pages = extract_text_from_pdf_bytes(pdf_bytes, filename)
    
    if not pages:
        logger.warning(f"[{filename}] No text extracted from PDF")
        return []
    
    chunks = chunk_documents(pages, chunk_size, chunk_overlap)
    logger.info(f"[{filename}] Created {len(chunks)} chunks from PDF")
    
    return chunks

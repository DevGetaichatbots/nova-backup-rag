"""
Azure Document Intelligence OCR Integration
============================================
Replaces PyPDF with Azure's AI-powered document analysis for better table extraction.
Required Environment Variables:
- AZURE_DOC_INTELLIGENCE_ENDPOINT: Your Azure endpoint URL
- AZURE_DOC_INTELLIGENCE_KEY: Your Azure API key
"""
import os
import re
import time
import logging
import requests
from typing import Optional, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureDocumentIntelligence:
    """
    Azure Document Intelligence OCR service.
    
    Usage:
        ocr = AzureDocumentIntelligence()
        result = ocr.extract_tables_from_pdf(pdf_bytes, "filename.pdf")
    """
    
    API_VERSION = "2024-11-30"
    
    def __init__(self):
        """Initialize with Azure credentials from environment variables."""
        self.endpoint = os.environ.get("AZURE_DOC_INTELLIGENCE_ENDPOINT", "").rstrip('/')
        self.key = os.environ.get("AZURE_DOC_INTELLIGENCE_KEY", "")
        
        if not self.endpoint or not self.key:
            raise ValueError(
                "Missing Azure credentials. Set AZURE_DOC_INTELLIGENCE_ENDPOINT "
                "and AZURE_DOC_INTELLIGENCE_KEY environment variables."
            )
        
        logger.info(f"Azure Document Intelligence initialized for: {self.endpoint}")
    
    def _is_valid_pdf(self, pdf_bytes: bytes) -> bool:
        """Check if bytes represent a valid PDF file."""
        return pdf_bytes[:4] == b'%PDF' if len(pdf_bytes) >= 4 else False
    
    def _submit_pdf(self, pdf_bytes: bytes, filename: str) -> Optional[str]:
        """
        Step 1: Submit PDF to Azure for analysis.
        Returns the operation URL for polling.
        """
        url = (
            f"{self.endpoint}/documentintelligence/documentModels/"
            f"prebuilt-layout:analyze?api-version={self.API_VERSION}"
            f"&outputContentFormat=markdown"
        )
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/pdf"
        }
        
        try:
            logger.info(f"[{filename}] Submitting PDF to Azure ({len(pdf_bytes)} bytes)...")
            response = requests.post(url, headers=headers, data=pdf_bytes, timeout=60)
            response.raise_for_status()
            
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                logger.error(f"[{filename}] No Operation-Location in response")
                return None
            
            logger.info(f"[{filename}] Operation started: {operation_url}")
            return operation_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[{filename}] Failed to submit PDF: {e}")
            return None
    
    def _poll_results(self, operation_url: str, filename: str, 
                      timeout: int = 120, poll_interval: int = 3) -> Optional[Dict]:
        """
        Step 2: Poll Azure until analysis is complete.
        Returns the full result when status is 'succeeded'.
        """
        headers = {"Ocp-Apim-Subscription-Key": self.key}
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                logger.error(f"[{filename}] Polling timeout after {timeout}s")
                return None
            
            try:
                response = requests.get(operation_url, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                status = result.get("status", "unknown")
                logger.info(f"[{filename}] Status: {status} (elapsed: {elapsed:.1f}s)")
                
                if status == "succeeded":
                    logger.info(f"[{filename}] Extraction complete!")
                    return result
                elif status == "failed":
                    error = result.get("error", {})
                    logger.error(f"[{filename}] Extraction failed: {error}")
                    return None
                elif status in ["notStarted", "running"]:
                    time.sleep(poll_interval)
                else:
                    logger.warning(f"[{filename}] Unknown status: {status}")
                    time.sleep(poll_interval)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"[{filename}] Polling error: {e}")
                time.sleep(poll_interval)
    
    def _parse_markdown_tables(self, result: Dict, filename: str) -> List[List[str]]:
        """
        Step 3: Parse markdown tables from Azure response.
        Returns list of rows, where each row is a list of cell values.
        """
        try:
            analyze_result = result.get("analyzeResult", {})
            content = analyze_result.get("content", "")
            
            if not content:
                logger.warning(f"[{filename}] No content in Azure response")
                return []
            
            logger.info(f"[{filename}] Received {len(content)} chars of markdown")
            
            rows = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                if not line or line.startswith('| ---') or re.match(r'^\|[\s\-:|]+\|$', line):
                    continue
                
                if line.startswith('|') and line.endswith('|'):
                    cells = [cell.strip() for cell in line.split('|')]
                    cells = [c for c in cells if c]
                    if cells:
                        rows.append(cells)
            
            logger.info(f"[{filename}] Parsed {len(rows)} rows from markdown")
            return rows
            
        except Exception as e:
            logger.error(f"[{filename}] Error parsing markdown: {e}")
            return []
    
    def _extract_pages_from_result(self, result: Dict, filename: str) -> List[Dict]:
        """
        Extract page-level content from Azure response for better metadata.
        Returns list of page dicts with content and page number.
        """
        try:
            analyze_result = result.get("analyzeResult", {})
            pages = analyze_result.get("pages", [])
            content = analyze_result.get("content", "")
            
            if not pages:
                if content:
                    return [{"content": content, "page_number": 1, "total_pages": 1}]
                return []
            
            page_contents = []
            for i, page in enumerate(pages):
                page_num = page.get("pageNumber", i + 1)
                spans = page.get("spans", [])
                
                page_text = ""
                for span in spans:
                    offset = span.get("offset", 0)
                    length = span.get("length", 0)
                    page_text += content[offset:offset + length]
                
                if page_text.strip():
                    page_contents.append({
                        "content": page_text,
                        "page_number": page_num,
                        "total_pages": len(pages)
                    })
            
            if not page_contents and content:
                return [{"content": content, "page_number": 1, "total_pages": 1}]
            
            logger.info(f"[{filename}] Extracted {len(page_contents)} pages")
            return page_contents
            
        except Exception as e:
            logger.error(f"[{filename}] Error extracting pages: {e}")
            if content:
                return [{"content": content, "page_number": 1, "total_pages": 1}]
            return []
    
    def extract_tables_from_pdf(self, pdf_bytes: bytes, filename: str = "document.pdf",
                                 timeout: int = 120) -> Dict:
        """
        Main method: Extract tables from PDF using Azure Document Intelligence.
        
        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Name of the file (for logging)
            timeout: Max seconds to wait for Azure (default 120)
        
        Returns:
            Dict with keys:
            - success: bool
            - rows: List of parsed rows (each row is a list of cell values)
            - raw_markdown: The raw markdown content from Azure
            - error: Error message if failed
        """
        if not self._is_valid_pdf(pdf_bytes):
            return {
                "success": False,
                "rows": [],
                "raw_markdown": "",
                "error": "Invalid PDF file (missing %PDF header)"
            }
        
        operation_url = self._submit_pdf(pdf_bytes, filename)
        if not operation_url:
            return {
                "success": False,
                "rows": [],
                "raw_markdown": "",
                "error": "Failed to submit PDF to Azure"
            }
        
        result = self._poll_results(operation_url, filename, timeout)
        if not result:
            return {
                "success": False,
                "rows": [],
                "raw_markdown": "",
                "error": "Azure analysis timed out or failed"
            }
        
        raw_markdown = result.get("analyzeResult", {}).get("content", "")
        rows = self._parse_markdown_tables(result, filename)
        
        return {
            "success": True,
            "rows": rows,
            "raw_markdown": raw_markdown,
            "error": None
        }
    
    def extract_text_from_pdf(self, pdf_bytes: bytes, filename: str = "document.pdf",
                               timeout: int = 120) -> str:
        """
        Extract full text/markdown from PDF (for vector store chunking).
        
        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Name of the file (for logging)
            timeout: Max seconds to wait for Azure
        
        Returns:
            Extracted text/markdown content as string, empty string on failure
        """
        result = self.extract_tables_from_pdf(pdf_bytes, filename, timeout)
        
        if result["success"]:
            return result["raw_markdown"]
        else:
            logger.error(f"[{filename}] Text extraction failed: {result['error']}")
            return ""
    
    def extract_pages_from_pdf(self, pdf_bytes: bytes, filename: str = "document.pdf",
                                timeout: int = 120) -> List[Dict]:
        """
        Extract page-level content from PDF for better metadata granularity.
        
        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Name of the file (for logging)
            timeout: Max seconds to wait for Azure
        
        Returns:
            List of dicts with 'content', 'page_number', 'total_pages'
        """
        if not self._is_valid_pdf(pdf_bytes):
            logger.error(f"[{filename}] Invalid PDF file")
            return []
        
        operation_url = self._submit_pdf(pdf_bytes, filename)
        if not operation_url:
            return []
        
        result = self._poll_results(operation_url, filename, timeout)
        if not result:
            return []
        
        return self._extract_pages_from_result(result, filename)
    
    @staticmethod
    def check_credentials() -> tuple[bool, str]:
        """
        Check if Azure Document Intelligence credentials are configured.
        Returns (is_valid, message)
        """
        endpoint = os.environ.get("AZURE_DOC_INTELLIGENCE_ENDPOINT", "")
        key = os.environ.get("AZURE_DOC_INTELLIGENCE_KEY", "")
        
        if not endpoint:
            return False, "AZURE_DOC_INTELLIGENCE_ENDPOINT not set"
        if not key:
            return False, "AZURE_DOC_INTELLIGENCE_KEY not set"
        
        return True, "Azure Document Intelligence credentials configured"

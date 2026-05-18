"""
Format Detector
===============
Identifies file type and source system from extension and binary header.
Phase 1 supports PDF and CSV only. Future phases add XER, XML, XLSX, Asta.
No external dependencies — pure stdlib byte inspection.
"""
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"
_XER_MARKERS = (b"ERPROJ", b"SYSASCT")
_MSP_MARKERS = (b"<Project", b"<?xml")
_XLSX_MAGIC = b"PK\x03\x04"


class FormatDetector:
    def detect(self, file_path: Path) -> tuple[str, str]:
        """
        Returns (MIME_TYPE, SOURCE_SYSTEM_IDENTIFIER).

        SOURCE_SYSTEM values: PDF | CSV | PRIMAVERA_XER | MSP_XML | EXCEL | UNKNOWN
        """
        ext = file_path.suffix.lower()

        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
        except OSError as e:
            logger.error(f"Cannot read file header: {e}")
            return ("application/octet-stream", "UNKNOWN")

        if header[:4] == _PDF_MAGIC:
            logger.debug(f"[{file_path.name}] Detected PDF by magic bytes")
            return ("application/pdf", "PDF")

        if any(m in header for m in _XER_MARKERS) or ext == ".xer":
            logger.debug(f"[{file_path.name}] Detected Primavera XER")
            return ("text/plain", "PRIMAVERA_XER")

        if header[:4] == _XLSX_MAGIC and ext in (".xlsx", ".xls"):
            logger.debug(f"[{file_path.name}] Detected Excel")
            return (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "EXCEL",
            )

        if (any(m in header for m in _MSP_MARKERS) and b"<Project" in header and ext == ".xml"):
            logger.debug(f"[{file_path.name}] Detected MS Project XML")
            return ("text/xml", "MSP_XML")

        if ext in (".csv", ".tsv"):
            logger.debug(f"[{file_path.name}] Detected CSV/TSV by extension")
            return ("text/csv", "CSV")

        try:
            header.decode("utf-8")
            if ext in (".csv", ".tsv") or b";" in header or b"," in header:
                logger.debug(f"[{file_path.name}] Detected CSV by content heuristic")
                return ("text/csv", "CSV")
        except UnicodeDecodeError:
            pass

        logger.warning(f"[{file_path.name}] Format unknown (ext={ext})")
        return ("application/octet-stream", "UNKNOWN")

    def detect_from_bytes(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        """Detect format from raw bytes and filename without writing to disk."""
        ext = Path(filename).suffix.lower()
        header = file_bytes[:1024]

        if header[:4] == _PDF_MAGIC:
            return ("application/pdf", "PDF")

        if any(m in header for m in _XER_MARKERS) or ext == ".xer":
            return ("text/plain", "PRIMAVERA_XER")

        if header[:4] == _XLSX_MAGIC and ext in (".xlsx", ".xls"):
            return (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "EXCEL",
            )

        if any(m in header for m in _MSP_MARKERS) and b"<Project" in header and ext == ".xml":
            return ("text/xml", "MSP_XML")

        if ext in (".csv", ".tsv"):
            return ("text/csv", "CSV")

        try:
            header.decode("utf-8")
            if b";" in header or b"," in header:
                return ("text/csv", "CSV")
        except UnicodeDecodeError:
            pass

        return ("application/octet-stream", "UNKNOWN")


detector = FormatDetector()

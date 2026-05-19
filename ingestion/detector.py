"""
Format Detector
===============
Identifies file type and source system from MIME type (python-magic) and binary header.
Uses python-magic when libmagic is available; falls back to pure binary header inspection
when the native library is not installed (e.g. Replit / NixOS without libmagic).
Supports: PDF, CSV, XLSX/XLS (Excel). Future phases add XER, XML, Asta.
"""
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"
_XER_MARKERS = (b"ERPROJ", b"SYSASCT")
_MSP_MARKERS = (b"<Project", b"<?xml")
_XLSX_MAGIC = b"PK\x03\x04"

try:
    import magic as _magic_lib
    _MAGIC_AVAILABLE = True
    logger.debug("python-magic/libmagic available — using MIME-type detection")
except (ImportError, Exception):
    _MAGIC_AVAILABLE = False
    logger.debug("libmagic not available — using binary header heuristics fallback")


def _mime_from_magic(file_path: Path) -> str:
    """Try MIME detection via python-magic; return '' on failure."""
    if not _MAGIC_AVAILABLE:
        return ""
    try:
        return _magic_lib.from_file(str(file_path), mime=True) or ""
    except Exception:
        return ""


def _mime_from_bytes_magic(data: bytes) -> str:
    """Try MIME detection from bytes via python-magic; return '' on failure."""
    if not _MAGIC_AVAILABLE:
        return ""
    try:
        return _magic_lib.from_buffer(data, mime=True) or ""
    except Exception:
        return ""


def _source_from_mime(mime: str, ext: str) -> str | None:
    """Map MIME type to SOURCE_SYSTEM string, or None if unknown."""
    if mime == "application/pdf":
        return "PDF"
    if mime in ("text/csv", "text/plain") and ext in (".csv", ".tsv"):
        return "CSV"
    if "spreadsheet" in mime or "excel" in mime:
        return "EXCEL"
    if mime == "text/xml":
        return "MSP_XML"
    return None


def _detect_by_header(header: bytes, ext: str) -> tuple[str, str]:
    """Pure binary-header + extension detection (libmagic fallback)."""
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


class FormatDetector:
    def detect(self, file_path: Path) -> tuple[str, str]:
        """
        Returns (MIME_TYPE, SOURCE_SYSTEM_IDENTIFIER).
        Tries python-magic first; falls back to byte-header inspection.
        SOURCE_SYSTEM values: PDF | CSV | PRIMAVERA_XER | MSP_XML | EXCEL | UNKNOWN
        """
        ext = file_path.suffix.lower()
        mime = _mime_from_magic(file_path)
        if mime:
            source = _source_from_mime(mime, ext)
            if source:
                logger.debug(f"[{file_path.name}] magic: {mime} → {source}")
                return (mime, source)

        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
        except OSError as e:
            logger.error(f"Cannot read file header: {e}")
            return ("application/octet-stream", "UNKNOWN")

        result = _detect_by_header(header, ext)
        logger.debug(f"[{file_path.name}] header heuristic → {result}")
        return result

    def detect_from_bytes(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        """Detect format from raw bytes and filename without writing to disk."""
        ext = Path(filename).suffix.lower()
        header = file_bytes[:1024]

        mime = _mime_from_bytes_magic(header)
        if mime:
            source = _source_from_mime(mime, ext)
            if source:
                logger.debug(f"[{filename}] magic: {mime} → {source}")
                return (mime, source)

        result = _detect_by_header(header, ext)
        logger.debug(f"[{filename}] header heuristic → {result}")
        return result


detector = FormatDetector()

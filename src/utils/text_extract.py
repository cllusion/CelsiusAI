"""Lightweight text extraction helpers for TXT, PDF, EPUB files.

This module uses optional imports at runtime and falls back to simple
approaches when heavy dependencies aren't available. It exposes a single
function `extract_text(path)` that returns (text, metadata).

Supported strategies (in order):
- TXT: read as UTF-8 with fallback encodings
- PDF: try pypdf (preferred) then PyPDF2, else return empty with message
- EPUB: try ebooklib to extract chapters, else return empty

The functions are defensive and will never raise on missing optional deps;
they return a helpful message in metadata for admin review.
"""

from pathlib import Path
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def _read_text_file(path: Path) -> Tuple[str, Dict]:
    encodings = ["utf-8", "latin-1", "utf-16"]
    for enc in encodings:
        try:
            with path.open("r", encoding=enc) as fh:
                return fh.read(), {"encoding": enc, "method": "txt"}
        except Exception:
            continue
    # last resort: binary read and decode ignoring errors
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="ignore")
        return text, {"encoding": "utf-8-ignored", "method": "txt"}
    except Exception as e:
        logger.exception("Failed reading text file %s", path)
        """Lightweight text extraction helpers for TXT, PDF and EPUB files.

        This module uses optional imports at runtime and falls back to simple
        approaches when heavy dependencies aren't available. It exposes a single
        function `extract_text(path)` that returns (text, metadata).

        Supported strategies (in order):
        - TXT: read as UTF-8 with fallback encodings
        - PDF: try pypdf (preferred) then PyPDF2
        - EPUB: try ebooklib to extract chapters

        The functions are defensive and will never raise on missing optional deps;
        they return a helpful message in metadata for admin review.
        """
        from pathlib import Path
        from typing import Dict, Tuple
        import logging

        logger = logging.getLogger(__name__)

        def _read_text_file(path: Path) -> Tuple[str, Dict]:
            encodings = ["utf-8", "latin-1", "utf-16"]
            for enc in encodings:
                try:
                    with path.open("r", encoding=enc) as fh:
                        return fh.read(), {"encoding": enc, "method": "txt"}
                except Exception:
                    continue
            # last resort: binary read and decode ignoring errors
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="ignore")
                return text, {"encoding": "utf-8-ignored", "method": "txt"}
            except Exception as e:
                logger.exception("Failed reading text file %s", path)
                return "", {"error": str(e), "method": "txt"}

        def _extract_pdf_pypdf(path: Path) -> Tuple[str, Dict]:
            try:
                import pypdf

                reader = pypdf.PdfReader(str(path))
                parts = []
                for page in getattr(reader, "pages", []):
                    try:
                        parts.append(page.extract_text() or "")
                    except Exception:
                        parts.append("")
                return "\n\n".join(parts), {"method": "pypdf", "pages": len(getattr(reader, "pages", []))}
            except Exception:
                return None

        def _extract_pdf_pypdf2(path: Path) -> Tuple[str, Dict]:
            try:
                import PyPDF2

                reader = PyPDF2.PdfReader(str(path))
                parts = []
                for page in getattr(reader, "pages", []):
                    try:
                        parts.append(page.extract_text() or "")
                    except Exception:
                        parts.append("")
                return "\n\n".join(parts), {"method": "PyPDF2", "pages": len(getattr(reader, "pages", []))}
            except Exception:
                return None

        def _extract_epub_ebooklib(path: Path) -> Tuple[str, Dict]:
            try:
                from ebooklib import epub
                from bs4 import BeautifulSoup

                book = epub.read_epub(str(path))
                parts = []
                for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
                    try:
                        soup = BeautifulSoup(item.get_content(), "html.parser")
                        parts.append(soup.get_text(separator="\n"))
                    except Exception:
                        continue
                return "\n\n".join(parts), {"method": "ebooklib", "items": len(parts)}
            except Exception:
                return None

        def extract_text(path: str) -> Tuple[str, Dict]:
            p = Path(path)
            if not p.exists():
                return "", {"error": "file_not_found"}

            suffix = p.suffix.lower()
            # TXT
            if suffix in {".txt", ".md", ".text"}:
                return _read_text_file(p)

            # PDF
            if suffix == ".pdf":
                res = _extract_pdf_pypdf(p)
                if res is not None:
                    return res
                res = _extract_pdf_pypdf2(p)
                if res is not None:
                    return res
                # No PDF libs available
                return "", {"error": "no_pdf_libs", "method": "pdf"}

            # EPUB
            if suffix in {".epub"}:
                res = _extract_epub_ebooklib(p)
                if res is not None:
                    return res
                return "", {"error": "no_epub_libs", "method": "epub"}

            # Unknown binary type: try plain text fallback
            try:
                return _read_text_file(p)
            except Exception as e:
                logger.exception("Unknown file type and read failed: %s", path)
                return "", {"error": str(e)}

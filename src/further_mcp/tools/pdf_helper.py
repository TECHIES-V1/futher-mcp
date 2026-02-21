from __future__ import annotations

from typing import List, Tuple, Dict, Union
import os

import fitz  # PyMuPDF

from .logger_config import get_logger, log_operation

logger = get_logger(__name__)


class PdfProcessingError(Exception):
    """Detailed errors raised during PDF processing."""

    def __init__(self, message: str, file_path: str, operation: str, original_error: Exception | None = None):
        self.message = message
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        super().__init__(f"{message} (file={file_path}, operation={operation})")


def _ensure_exists(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF file not found: {path}")


@log_operation("pdf_listing")
def get_all_pdf_files(directory: str) -> List[str]:
    return [entry for entry in os.listdir(directory) if entry.lower().endswith(".pdf")]


@log_operation("pdf_metadata_extraction")
def get_meta(pdf_path: str) -> Dict[str, Union[str, int, bool]]:
    _ensure_exists(pdf_path)
    doc = fitz.open(pdf_path)
    meta = {k: v for k, v in doc.metadata.items() if v}
    meta["pages"] = doc.page_count
    meta["file_size"] = os.path.getsize(pdf_path)
    try:
        meta["pdf_version"] = f"{doc.version_major}.{doc.version_minor}"
    except AttributeError:
        meta["pdf_version"] = str(getattr(doc, "version", "unknown"))
    meta["is_encrypted"] = doc.is_encrypted
    if doc.page_count:
        rect = doc[0].rect
        meta["page_width"] = rect.width
        meta["page_height"] = rect.height
    doc.close()
    logger.info("Collected PDF metadata", file_path=pdf_path, metadata_fields=list(meta.keys()))
    return meta


@log_operation("pdf_toc_extraction")
def get_toc(pdf_path: str) -> List[Tuple[str, int]]:
    _ensure_exists(pdf_path)
    doc = fitz.open(pdf_path)
    toc_data = doc.get_toc()
    doc.close()
    return [(title, page) for _, title, page in toc_data]


def extract_page_text(pdf_path: str, page_number: int) -> str:
    _ensure_exists(pdf_path)
    doc = fitz.open(pdf_path)
    try:
        text = doc[page_number - 1].get_text()
    except Exception as exc:
        raise PdfProcessingError("Failed to extract page text", pdf_path, "page_text", exc)
    finally:
        doc.close()
    return text


def extract_page_markdown(pdf_path: str, page_number: int) -> str:
    _ensure_exists(pdf_path)
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_number - 1]
        blocks = page.get_text("dict")["blocks"]
        lines = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    text_parts = []
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        size = span.get("size", 0)
                        flags = span.get("flags", 0)
                        if size > 14:
                            text = f"## {text}"
                        if flags & 2**3:
                            text = f"**{text}**"
                        if flags & 2**1:
                            text = f"*{text}*"
                        text_parts.append(text)
                    if text_parts:
                        lines.append(" ".join(text_parts))
        return "\n".join(lines)
    finally:
        doc.close()


def extract_chapter_by_title(pdf_path: str, chapter_title: str) -> Tuple[str, List[int]]:
    toc = get_toc(pdf_path)
    start_page = None
    end_page = None
    for idx, (title, page) in enumerate(toc):
        if chapter_title.lower() in title.lower():
            start_page = page
            if idx + 1 < len(toc):
                end_page = toc[idx + 1][1]
            break
    if start_page is None:
        raise PdfProcessingError("Chapter not found", pdf_path, "chapter_lookup")
    doc = fitz.open(pdf_path)
    last_page = doc.page_count
    doc.close()
    end_page = end_page or last_page
    pages = []
    for page_num in range(start_page, end_page):
        pages.append(extract_page_text(pdf_path, page_num))
    return ("\n".join(pages), list(range(start_page, end_page)))

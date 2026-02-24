from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import fitz

from .tools import ebook_helper, pdf_helper, get_logger

logger = get_logger(__name__)


def _guess_extension(url: str, headers: dict[str, str]) -> str:
    parsed = urlparse(url)
    if suffix := Path(parsed.path).suffix:
        return suffix

    content_type = headers.get("content-type", "")
    ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
    return ext or ".bin"


def download_book(url: str, root: Path) -> Path:
    destination_dir = root / "downloaded"
    destination_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            suffix = _guess_extension(url, response.headers)
            base_name = Path(urlparse(url).name or "book")
            file_path = destination_dir / f"{uuid4().hex}_{base_name}{suffix}"
            with file_path.open("wb") as handle:
                for chunk in response.iter_bytes(8192):
                    handle.write(chunk)
    logger.info("Downloaded book to disk", file_path=str(file_path))
    return file_path


def _collect_text(chunks: Iterable[str], limit: int) -> str:
    collected = []
    for chunk in chunks:
        collected.append(chunk.strip())
        if len(collected) >= limit:
            break
    return "\n\n".join(collected)


def parse_book(file_path: Path, limit_pages: int = 3, limit_chapters: int = 3) -> dict[str, str | int]:
    suffix = file_path.suffix.lower()
    summary = ""
    if suffix == ".pdf":
        doc = fitz.open(file_path)
        total_pages = doc.page_count
        doc.close()
        texts = [
            pdf_helper.extract_page_text(str(file_path), page + 1)
            for page in range(min(limit_pages, total_pages))
        ]
        summary = _collect_text(texts, limit_pages)
        fmt = "pdf"
    elif suffix in {".epub", ".opf"}:
        toc = ebook_helper.get_toc(str(file_path))
        texts = []
        for title, href in toc[:limit_chapters]:
            try:
                texts.append(ebook_helper.extract_chapter_plain_text(str(file_path), href))
            except Exception as exc:
                logger.warning("Failed to parse EPUB chapter", chapter=title, error=str(exc))
        summary = _collect_text(texts, limit_chapters)
        fmt = "epub"
    else:
        summary = file_path.read_text(errors="ignore")[:4096]
        fmt = suffix.lstrip(".")

    return {
        "relative_path": str(file_path.name),
        "format": fmt,
        "size_bytes": file_path.stat().st_size,
        "summary": summary,
    }

from __future__ import annotations

from typing import List, Tuple, Dict, Union, Any
import os
from bs4 import BeautifulSoup, Comment
from html2text import HTML2Text

from ebooklib import epub

from .logger_config import get_logger, log_operation

logger = get_logger(__name__)


class EpubProcessingError(Exception):
    """Detailed errors raised during EPUB processing."""

    def __init__(self, message: str, file_path: str, operation: str, original_error: Exception | None = None):
        self.message = message
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        super().__init__(f"{message} (file={file_path}, operation={operation})")


def _ensure_exists(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"EPUB file not found: {path}")


@log_operation("epub_listing")
def get_all_epub_files(directory: str) -> List[str]:
    return [entry for entry in os.listdir(directory) if entry.lower().endswith(".epub")]


@log_operation("epub_metadata_extraction")
def get_meta(epub_path: str) -> Dict[str, Union[str, List[str]]]:
    _ensure_exists(epub_path)
    book = epub.read_epub(epub_path)
    meta: Dict[str, Union[str, List[str]]] = {}

    for key, attr in {
        "title": "title",
        "language": "language",
        "identifier": "identifier",
        "date": "date",
        "publisher": "publisher",
        "description": "description",
    }.items():
        values = book.get_metadata("DC", attr)
        if values and values[0]:
            meta[key] = values[0][0]

    for key in ("creator", "contributor", "subject"):
        values = book.get_metadata("DC", key)
        if values:
            meta[key] = [item[0] for item in values if item]

    logger.info("Collected EPUB metadata", file_path=epub_path, metadata_fields=list(meta.keys()))
    return meta


@log_operation("epub_toc_extraction")
def get_toc(epub_path: str) -> List[Tuple[str, str]]:
    _ensure_exists(epub_path)
    book = epub.read_epub(epub_path)
    toc_entries: List[Tuple[str, str]] = []

    def _collect(items):
        for item in items:
            if isinstance(item, tuple):
                link, children = item
                toc_entries.append((link.title, link.href))
                _collect(children)
            else:
                toc_entries.append((item.title, item.href))

    _collect(book.toc)
    logger.info("Extracted EPUB TOC entries", file_path=epub_path, chapter_count=len(toc_entries))
    return toc_entries


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "img", "svg", "iframe", "video", "nav"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all():
        if not tag.get_text(strip=True) and not tag.find("img") and tag.name not in ("br",):
            tag.decompose()
    return str(soup)


def _convert_html_to_markdown(html: str) -> str:
    converter = HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    return converter.handle(html)


@log_operation("epub_chapter_conversion")
def extract_chapter_markdown(epub_path: str, chapter_href: str) -> str:
    _ensure_exists(epub_path)
    book = epub.read_epub(epub_path)
    html = _extract_chapter_html(book, chapter_href, epub_path)
    return _convert_html_to_markdown(html)


def _extract_chapter_html(book: Any, chapter_href: str, epub_path: str) -> str:
    if "#" in chapter_href:
        href, anchor = chapter_href.split("#", 1)
    else:
        href, anchor = chapter_href, None

    item = book.get_item_with_href(href)
    if item is None:
        raise EpubProcessingError(f"Chapter not found: {href}", file_path=epub_path, operation="chapter_lookup")

    soup = BeautifulSoup(item.get_content(), "html.parser")
    if anchor:
        element = soup.find(id=anchor)
        if element is None:
            raise EpubProcessingError(f"Anchor not found: {anchor}", file_path=epub_path, operation="chapter_lookup")
        fragments = [str(element)]
        for node in element.find_all_next():
            fragments.append(str(node))
        return _clean_html("\n".join(fragments))

    return _clean_html(str(soup))


def extract_chapter_plain_text(epub_path: str, chapter_href: str) -> str:
    _ensure_exists(epub_path)
    book = epub.read_epub(epub_path)
    html = _extract_chapter_html(book, chapter_href, epub_path)
    plain = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    return plain.strip()

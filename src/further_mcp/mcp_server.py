from __future__ import annotations

import inspect
import os
from functools import wraps
from pathlib import Path
from typing import Sequence

from fastmcp import FastMCP

from .discovery import DiscoveryProvider
from .pipeline import download_book, parse_book
from .providers import OpenLibraryProvider
from .models import AuthorDetails, OpenLibrary
from .tools import ebook_helper, pdf_helper, setup_logger, get_logger

setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))
LOGGER = get_logger(__name__)

ROOT_PATH = Path.home() / "ebooks"
ROOT_PATH.mkdir(parents=True, exist_ok=True)


def _resolve_path(path: str) -> Path:
    candidate = (ROOT_PATH / path).resolve()
    if not str(candidate).startswith(str(ROOT_PATH)):
        raise FileNotFoundError("Access to the requested file is not allowed.")
    if not candidate.exists():
        raise FileNotFoundError("Requested file does not exist.")
    return candidate


def _handle_file_operation(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            LOGGER.error("File operation failed", error_type=type(exc).__name__, error_details=str(exc))
            raise

    wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
    return wrapper


MCP_APP = FastMCP(name="further-mcp", version="0.1.0")


@MCP_APP.tool()
async def search_books(
    query: str,
    keywords: Sequence[str] | None = None,
    limit: int = 10,
) -> OpenLibrary:
    LOGGER.info("search_books called", query=query, keywords=keywords, limit=limit)
    provider = OpenLibraryProvider()
    result = await provider.search_books(query, keywords=keywords, limit=limit)
    return result


@MCP_APP.tool()
async def search_author(query: str) -> AuthorDetails:
    LOGGER.info("search_author called", query=query)
    provider = OpenLibraryProvider()
    return await provider.search_author(query)


@MCP_APP.tool()
async def search_author_with_book_name(query: str) -> AuthorDetails:
    LOGGER.info("search_author_with_book_name called", query=query)
    provider = OpenLibraryProvider()
    return await provider.search_author_with_book_name(query)


@MCP_APP.tool()
async def discover_books(
    query: str,
    sources: Sequence[str] | None = None,
    limit: int = 5,
) -> dict:
    LOGGER.info("discover_books called", query=query, sources=sources, limit=limit)
    provider = DiscoveryProvider()
    return await provider.discover_books(query=query, sources=sources, limit=limit)


@MCP_APP.tool()
def fetch_and_parse_book(
    url: str,
    limit_pages: int = 3,
    limit_chapters: int = 3,
) -> dict:
    LOGGER.info("fetch_and_parse_book called", url=url)
    file_path = download_book(url, ROOT_PATH)
    return parse_book(file_path, limit_pages=limit_pages, limit_chapters=limit_chapters)


@MCP_APP.tool()
@_handle_file_operation
def list_ebooks() -> dict[str, list[str]]:
    return {
        "epub": ebook_helper.get_all_epub_files(str(ROOT_PATH)),
        "pdf": pdf_helper.get_all_pdf_files(str(ROOT_PATH)),
    }


@MCP_APP.tool()
@_handle_file_operation
def get_epub_metadata(relative_path: str) -> dict:
    target = _resolve_path(relative_path)
    return ebook_helper.get_meta(str(target))


@MCP_APP.tool()
@_handle_file_operation
def get_pdf_metadata(relative_path: str) -> dict:
    target = _resolve_path(relative_path)
    return pdf_helper.get_meta(str(target))


@MCP_APP.tool()
@_handle_file_operation
def get_epub_toc(relative_path: str) -> list[tuple[str, str]]:
    target = _resolve_path(relative_path)
    return ebook_helper.get_toc(str(target))


@MCP_APP.tool()
@_handle_file_operation
def get_pdf_toc(relative_path: str) -> list[tuple[str, int]]:
    target = _resolve_path(relative_path)
    return pdf_helper.get_toc(str(target))


@MCP_APP.tool()
@_handle_file_operation
def get_epub_chapter_markdown(relative_path: str, chapter_id: str) -> str:
    target = _resolve_path(relative_path)
    return ebook_helper.extract_chapter_markdown(str(target), chapter_id)


@MCP_APP.tool()
@_handle_file_operation
def get_pdf_chapter_text(relative_path: str, chapter_title: str) -> dict:
    target = _resolve_path(relative_path)
    content, pages = pdf_helper.extract_chapter_by_title(str(target), chapter_title)
    return {"content": content, "pages": pages}


def main() -> None:
    LOGGER.info("Starting Further MCP FastMCP server")
    MCP_APP.run()


if __name__ == "__main__":
    main()

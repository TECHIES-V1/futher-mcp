from __future__ import annotations

import os
from pathlib import Path
from typing import List, Sequence

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from fastapi.middleware.cors import CORSMiddleware

from .discovery import DiscoveryProvider
from .pipeline import download_book, parse_book
from .providers import OpenLibraryProvider
from .tools import ebook_helper, pdf_helper, setup_logger, get_logger

load_dotenv()

setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))

LOGGER = get_logger(__name__)
LOGGER.info("Starting Further MCP FastAPI module")

APP = FastAPI(
    title="Further-MCP",
    description="Combined ebook conversion and OpenLibrary search MCP.",
    version="0.1.0",
)

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

EBOOK_ROOT = Path(os.getenv("EBOOK_ROOT_PATH", "ebooks")).resolve()
EBOOK_ROOT.mkdir(parents=True, exist_ok=True)


def resolve_ebook_path(relative_path: str) -> Path:
    candidate = (EBOOK_ROOT / relative_path).resolve()
    if not str(candidate).startswith(str(EBOOK_ROOT)):
        raise HTTPException(status_code=403, detail="File outside allowed path")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


@APP.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "further-mcp"}


@APP.get("/search")
async def search_books(
    query: str = Query(..., min_length=1),
    keywords: Sequence[str] | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    provider = OpenLibraryProvider()
    try:
        result = await provider.search_books(query, keywords=keywords, limit=limit)
        return result.model_dump()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@APP.get("/search_author")
async def search_author(query: str = Query(..., min_length=1)) -> dict:
    provider = OpenLibraryProvider()
    try:
        result = await provider.search_author(query)
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@APP.get("/ebooks/list")
def list_ebooks() -> dict[str, list[str]]:
    epub_files = ebook_helper.get_all_epub_files(str(EBOOK_ROOT))
    pdf_files = pdf_helper.get_all_pdf_files(str(EBOOK_ROOT))
    return {"epub": epub_files, "pdf": pdf_files}


@APP.get("/ebooks/metadata")
def ebook_metadata(path: str = Query(...)) -> dict:
    resolved = resolve_ebook_path(path)
    if resolved.suffix.lower() == ".epub":
        return ebook_helper.get_meta(str(resolved))
    if resolved.suffix.lower() == ".pdf":
        return pdf_helper.get_meta(str(resolved))
    raise HTTPException(status_code=415, detail="Unsupported file type")


@APP.get("/ebooks/toc")
def ebook_table_of_contents(path: str = Query(...)) -> dict:
    resolved = resolve_ebook_path(path)
    if resolved.suffix.lower() == ".epub":
        return {"toc": ebook_helper.get_toc(str(resolved))}
    if resolved.suffix.lower() == ".pdf":
        return {"toc": pdf_helper.get_toc(str(resolved))}
    raise HTTPException(status_code=415, detail="Unsupported file type")


@APP.get("/ebooks/epub/chapter-markdown")
def epub_chapter_markdown(path: str = Query(...), chapter: str = Query(..., min_length=1)) -> dict:
    resolved = resolve_ebook_path(path)
    if resolved.suffix.lower() != ".epub":
        raise HTTPException(status_code=415, detail="EPUB required")
    content = ebook_helper.extract_chapter_markdown(str(resolved), chapter)
    return {"markdown": content}


@APP.get("/ebooks/pdf/chapter-text")
def pdf_chapter_text(path: str = Query(...), chapter_title: str = Query(..., min_length=1)) -> dict:
    resolved = resolve_ebook_path(path)
    if resolved.suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="PDF required")
    content, pages = pdf_helper.extract_chapter_by_title(str(resolved), chapter_title)
    return {"content": content, "pages": pages}


def _normalize_sources(sources: List[str] | None) -> list[str] | None:
    if not sources:
        return None
    return [source.strip().lower() for source in sources if source.strip()]


class PipelineRequest(BaseModel):
    url: HttpUrl
    limit_pages: int = Field(3, ge=1, le=12)
    limit_chapters: int = Field(3, ge=1, le=12)


@APP.get("/discovery/search")
async def discovery_search(
    query: str = Query(..., min_length=1),
    sources: List[str] | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
) -> dict:
    provider = DiscoveryProvider()
    normalized = _normalize_sources(sources)
    return await provider.discover_books(query=query, sources=normalized, limit=limit)


@APP.get("/discovery/gutendex")
async def discovery_gutendex(query: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=20)) -> dict:
    provider = DiscoveryProvider()
    return (await provider.gutendex_search(query=query, limit=limit)).model_dump()


@APP.get("/discovery/openlibrary")
async def discovery_openlibrary(
    query: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
) -> dict:
    provider = DiscoveryProvider()
    return (await provider.openlibrary_search(query=query, limit=limit)).model_dump()


@APP.get("/discovery/standard-ebooks")
async def discovery_standard_ebooks(
    query: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
) -> dict:
    provider = DiscoveryProvider()
    return (await provider.standard_ebooks_search(query=query, limit=limit)).model_dump()


@APP.post("/pipeline/fetch-parse")
def pipeline_fetch_parse(request: PipelineRequest) -> dict:
    file_path = download_book(request.url, EBOOK_ROOT)
    return parse_book(file_path, limit_pages=request.limit_pages, limit_chapters=request.limit_chapters)


def start_fastapi(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run("further_mcp.fastapi_server:APP", host=host, port=port)

from __future__ import annotations

import asyncio
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Sequence

import httpx

from .models import BookFormatLink, DiscoveryBook, DiscoveryResponse
from .tools import get_logger

logger = get_logger(__name__)


class DiscoveryProvider:
    """Query multiple public-domain catalogs for downloadable EPUB/PDF links."""

    def __init__(
        self,
        gutendex_url: str | None = None,
        openlibrary_url: str | None = None,
        standard_url: str | None = None,
    ):
        self.gutendex_url = gutendex_url or os.getenv("GUTENDEX_BASE_URL", "https://gutendex.com/books/")
        self.openlibrary_url = openlibrary_url or os.getenv("OPENLIBRARY_SEARCH_URL", "https://openlibrary.org/search.json")
        self.archive_base = os.getenv("OPENARCHIVE_BASE_URL", "https://archive.org/download")
        self.standard_url = standard_url or os.getenv("STANDARD_EBOOKS_OPDS_URL", "https://standardebooks.org/opds")

    async def _fetch_json(self, url: str, params: dict[str, str] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            logger.debug("Discovery JSON request", url=url, params=params)
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def _fetch_xml(self, url: str, params: dict[str, str] | None = None) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            logger.debug("Discovery XML request", url=url, params=params)
            response = await client.get(url, params=params, headers={"Accept": "application/atom+xml,application/xml"})
            response.raise_for_status()
            return response.text

    def _build_gutendex_links(self, formats: dict[str, str]) -> list[BookFormatLink]:
        links: list[BookFormatLink] = []
        for media_type, url in formats.items():
            if not url or url.endswith(".gif"):
                continue
            links.append(BookFormatLink(format=media_type, url=url))
        return links

    async def gutendex_search(self, query: str, limit: int = 5) -> DiscoveryResponse:
        params = {"search": query, "page": "1"}
        payload = await self._fetch_json(self.gutendex_url, params)
        results = payload.get("results", [])[:limit]
        books = []
        for item in results:
            authors = [author.get("name") for author in item.get("authors", []) if author.get("name")]
            download_links = self._build_gutendex_links(item.get("formats", {}))
            books.append(
                DiscoveryBook(
                    title=item.get("title"),
                    authors=authors,
                    year=item.get("copyright_year"),
                    source="gutendex",
                    source_id=str(item.get("id")),
                    download_links=download_links,
                    extra={"subjects": item.get("subjects", [])},
                )
            )
        return DiscoveryResponse(
            source="gutendex",
            query=query,
            total_results=payload.get("count"),
            books=books,
        )

    def _build_openlibrary_links(self, ia_id: str) -> list[BookFormatLink]:
        return [
            BookFormatLink(format="pdf", url=f"{self.archive_base}/{ia_id}/{ia_id}.pdf"),
            BookFormatLink(format="epub", url=f"{self.archive_base}/{ia_id}/{ia_id}.epub"),
        ]

    async def openlibrary_search(self, query: str, limit: int = 5) -> DiscoveryResponse:
        params = {"q": query, "limit": str(limit)}
        payload = await self._fetch_json(self.openlibrary_url, params)
        docs = payload.get("docs", [])[:limit]
        books = []
        for doc in docs:
            authors = doc.get("author_name") or []
            ia_ids = doc.get("ia") or []
            download_links = []
            for ia in ia_ids[:2]:
                download_links.extend(self._build_openlibrary_links(ia))
            books.append(
                DiscoveryBook(
                    title=doc.get("title"),
                    authors=authors,
                    year=doc.get("first_publish_year"),
                    source="openlibrary",
                    source_id=doc.get("key"),
                    description=doc.get("subtitle"),
                    download_links=download_links,
                    extra={"publishers": doc.get("publisher")},
                )
            )
        return DiscoveryResponse(
            source="openlibrary",
            query=query,
            total_results=payload.get("numFound"),
            books=books,
        )

    async def standard_ebooks_search(self, query: str, limit: int = 5) -> DiscoveryResponse:
        params = {"search": query}
        xml_text = await self._fetch_xml(self.standard_url, params)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_text)
        entries = root.findall("atom:entry", ns)[:limit]
        books = []
        for entry in entries:
            title = entry.findtext("atom:title", default=None, namespaces=ns)
            authors = [
                author.findtext("atom:name", namespaces=ns)
                for author in entry.findall("atom:author", ns)
                if author.findtext("atom:name", namespaces=ns)
            ]
            summary = entry.findtext("atom:summary", default=None, namespaces=ns)
            download_links = []
            for link in entry.findall("atom:link", ns):
                rel = link.get("rel", "")
                href = link.get("href")
                mime = link.get("type")
                if not href:
                    continue
                if "acquisition" in rel.lower() or mime in {"application/epub+zip", "application/pdf"}:
                    download_links.append(BookFormatLink(format=mime or rel, url=href, label=rel))
            books.append(
                DiscoveryBook(
                    title=title,
                    authors=[a for a in authors if a],
                    source="standard-ebooks",
                    source_id=entry.findtext("atom:id", namespaces=ns),
                    description=summary,
                    download_links=download_links,
                )
            )
        return DiscoveryResponse(source="standard-ebooks", query=query, books=books, total_results=len(books))

    async def discover_books(
        self,
        query: str,
        sources: Sequence[str] | None = None,
        limit: int = 5,
    ) -> dict:
        if not sources:
            sources = ("gutendex", "openlibrary", "standard")
        tasks = []
        for source in sources:
            if source == "gutendex":
                tasks.append(self.gutendex_search(query, limit=limit))
            elif source == "openlibrary":
                tasks.append(self.openlibrary_search(query, limit=limit))
            elif source in {"standard", "standard-ebooks"}:
                tasks.append(self.standard_ebooks_search(query, limit=limit))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for response in responses:
            if isinstance(response, Exception):
                logger.warning("Discovery source failed", error=str(response))
                continue
            results.append(response.model_dump())
        return {"query": query, "responses": results, "timestamp": datetime.utcnow().isoformat()}

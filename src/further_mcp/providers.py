from __future__ import annotations

import logging
import os
from typing import Sequence

import httpx

from .models import AuthorDetails, AuthorWorks, OpenLibrary

logger = logging.getLogger(__name__)


class OpenLibraryProvider:
    """Bridge to the OpenLibrary APIs with keyword-aware query building."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("OPENLIBRARY_BASE_URL", "https://openlibrary.org")
        logger.info("Initialized OpenLibraryProvider with %s", self.base_url)

    def _build_query(self, query: str, keywords: Sequence[str] | None = None) -> str:
        tokens = []
        normalized = []

        if query.strip():
            tokens.append(query.strip())

        if keywords:
            tokens.extend([token.strip() for token in keywords if token.strip()])

        synonyms = {"intro": "introduction", "updated": "latest", "python": "python"}
        seen = set()

        for token in tokens:
            normalized_token = synonyms.get(token.lower(), token.lower())
            if normalized_token not in seen:
                seen.add(normalized_token)
                normalized.append(normalized_token)

        return " ".join(normalized)

    async def _get_json(self, path: str, params: dict[str, str]) -> dict:
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=30) as client:
            logger.debug("Calling OpenLibrary API: %s with params %s", url, params)
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def search_books(self, query: str, keywords: Sequence[str] | None = None, limit: int = 15) -> OpenLibrary:
        refined_query = self._build_query(query, keywords)
        params = {"q": refined_query, "format": "json", "limit": str(limit)}
        data = await self._get_json("/search.json", params)
        data.setdefault("q", refined_query)
        return OpenLibrary(**data)

    async def search_author_with_book_name(self, query: str) -> AuthorDetails:
        books = await self.search_books(query, limit=1)
        if not books.docs:
            raise ValueError("No books found for query.")
        author_id = books.docs[0].author_key or books.docs[0].author_name
        author_id = author_id or ""
        data = await self._get_json(f"/authors/{author_id}.json", {})
        author = AuthorDetails(**data)
        author.works = await self.search_author_works(author_id)
        return author

    async def search_author(self, query: str) -> AuthorDetails:
        params = {"q": query}
        data = await self._get_json("/search/authors.json", params)
        doc = data.get("docs", [None])[0]
        if not doc:
            raise ValueError("Author not found.")
        author = AuthorDetails(**doc)
        author.works = await self.search_author_works(author_id=author.key or "")
        return author

    async def search_author_works(self, author_id: str) -> list[AuthorWorks]:
        data = await self._get_json(f"/authors/{author_id}/works.json", {})
        entries = data.get("entries", [])
        return [AuthorWorks(**entry) for entry in entries[:10]]

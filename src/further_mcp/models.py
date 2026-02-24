from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookDetails(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True)
    author_name: str | None = Field(None)
    author_key: str | None = Field(None)
    edition_count: int | None = Field(None, ge=0)
    first_publish_year: int | None = Field(None, ge=1000, le=datetime.now().year + 1)
    language: str | list[str] | None = Field(None)
    title: str | None = Field(None)

    @field_validator("author_name", "author_key", mode="before")
    def ensure_string(cls, value: str | list[str] | None) -> str | None:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @field_validator("language", mode="before")
    def normalize_language(cls, value: str | list[str] | None) -> str | None:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @field_validator("title", mode="before")
    def clean_title(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip()


class BookFormatLink(BaseModel):
    format: str
    url: str
    label: str | None = None


class DiscoveryBook(BaseModel):
    title: str | None = Field(None)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(None)
    source: str = Field(...)
    source_id: str | None = Field(None)
    description: str | None = Field(None)
    download_links: list[BookFormatLink] = Field(default_factory=list)
    extra: dict[str, Any] | None = Field(None)


class DiscoveryResponse(BaseModel):
    source: str
    query: str
    total_results: int | None = None
    books: list[DiscoveryBook] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OpenLibrary(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True)
    num_found: int = Field(default=0)
    q: str = Field(default="")
    docs: list[BookDetails] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)


class AuthorWorks(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True)
    author_id: str | None = Field(None)
    title: str | None = Field(None)
    subtitle: str | None = Field(None)


class AuthorDetails(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True)
    key: str | None = Field(None)
    name: str | None = Field(None)
    alternate_names: list[str] | None = Field(None)
    bio: str | None = Field(None)
    birth_date: str | None = Field(None)
    death_date: str | None = Field(None)
    fuller_name: str | None = Field(None)
    works: list[AuthorWorks] | None = Field(default_factory=list)
    top_subjects: list[str] | None = Field(None)

    def add_author_works(self, works: list[AuthorWorks]) -> None:
        if self.works is None:
            self.works = []
        self.works.extend(works)

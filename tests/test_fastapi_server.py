from pathlib import Path

import pytest
from fastapi import HTTPException

import further_mcp.fastapi_server as fastapi_server


def test_resolve_ebook_path_within_root(tmp_path, monkeypatch):
    root = tmp_path / "ebooks"
    root.mkdir()
    target = root / "book.epub"
    target.write_text("content")

    monkeypatch.setattr(fastapi_server, "EBOOK_ROOT", root)
    resolved = fastapi_server.resolve_ebook_path("book.epub")
    assert resolved == target


def test_resolve_ebook_path_rejects_escape(tmp_path, monkeypatch):
    root = tmp_path / "ebooks"
    root.mkdir()
    monkeypatch.setattr(fastapi_server, "EBOOK_ROOT", root)
    with pytest.raises(HTTPException) as exc_info:
        fastapi_server.resolve_ebook_path("../secret.txt")
    assert exc_info.value.status_code == 403

from pathlib import Path

import pytest

from further_mcp import mcp_server


def test_list_ebooks_picks_up_files(tmp_path, monkeypatch):
    root = tmp_path / "library"
    root.mkdir()
    (root / "intro.epub").write_text("ebook")
    (root / "guide.pdf").write_text("pdf")

    monkeypatch.setattr(mcp_server, "ROOT_PATH", root)
    result = mcp_server.list_ebooks()

    assert result["epub"] == ["intro.epub"]
    assert result["pdf"] == ["guide.pdf"]


@pytest.mark.asyncio
async def test_discover_books_tool(monkeypatch):
    async def fake_discover(self, query, sources, limit):
        return {"query": query, "responses": []}

    monkeypatch.setattr(
        mcp_server.DiscoveryProvider,
        "discover_books",
        fake_discover,
    )

    result = await mcp_server.discover_books("ai", sources=["gutendex"], limit=1)
    assert result["query"] == "ai"

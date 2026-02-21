from pathlib import Path

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

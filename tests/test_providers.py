from further_mcp.providers import OpenLibraryProvider


def test_build_query_normalizes_keywords():
    provider = OpenLibraryProvider()
    result = provider._build_query("Python", ["Introduction", "Updated", "Python"])
    assert result.split() == ["python", "introduction", "latest"]


def test_build_query_ignores_empty_keywords():
    provider = OpenLibraryProvider()
    result = provider._build_query("Python", ["", "   ", "Updated"])
    assert "updated" not in result
    assert "latest" in result

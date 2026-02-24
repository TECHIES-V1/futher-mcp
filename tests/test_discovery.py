import pytest

from further_mcp.discovery import DiscoveryProvider
from further_mcp.models import DiscoveryResponse


@pytest.mark.asyncio
async def test_gutendex_search_parses_formats(monkeypatch):
    provider = DiscoveryProvider()

    async def fake_fetch(url, params=None):
        return {
            "count": 1,
            "results": [
                {
                    "id": 123,
                    "title": "Sample Book",
                    "copyright_year": 1990,
                    "authors": [{"name": "Reader"}],
                    "formats": {
                        "application/epub+zip": "https://example.com/book.epub",
                        "text/plain; charset=utf-8": "https://example.com/book.txt",
                    },
                    "subjects": ["AI"],
                }
            ],
        }

    monkeypatch.setattr(provider, "_fetch_json", fake_fetch)
    response = await provider.gutendex_search("sample", limit=1)

    assert response.source == "gutendex"
    assert len(response.books) == 1
    book = response.books[0]
    assert book.download_links
    assert any(link.format.startswith("application/epub") for link in book.download_links)


@pytest.mark.asyncio
async def test_openlibrary_search_adds_archive_links(monkeypatch):
    provider = DiscoveryProvider()

    async def fake_fetch(url, params=None):
        return {
            "numFound": 1,
            "docs": [
                {
                    "title": "Mystery",
                    "author_name": ["Detective"],
                    "first_publish_year": 1920,
                    "key": "/works/OL1W",
                    "ia": ["Mystery123"],
                }
            ],
        }

    monkeypatch.setattr(provider, "_fetch_json", fake_fetch)
    response = await provider.openlibrary_search("mystery", limit=1)
    assert response.source == "openlibrary"
    assert response.books[0].download_links
    assert any("Mystery123" in link.url for link in response.books[0].download_links)


@pytest.mark.asyncio
async def test_standard_ebooks_parses_opds(monkeypatch):
    provider = DiscoveryProvider()
    sample_feed = """
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>urn:sample</id>
                <title>Fresh Title</title>
                <author><name>Creator</name></author>
                <summary>Clean EPUB</summary>
                <link rel="http://opds-spec.org/acquisition" href="https://standardebooks.org/book.epub" type="application/epub+zip"/>
            </entry>
        </feed>
    """

    async def fake_fetch_xml(url, params=None):
        return sample_feed

    monkeypatch.setattr(provider, "_fetch_xml", fake_fetch_xml)
    response = await provider.standard_ebooks_search("fresh", limit=1)
    assert response.source == "standard-ebooks"
    assert response.books[0].title == "Fresh Title"
    assert response.books[0].download_links[0].url.endswith(".epub")


@pytest.mark.asyncio
async def test_discover_books_aggregates(monkeypatch):
    provider = DiscoveryProvider()

    async def stub_response(source):
        return DiscoveryResponse(source=source, query="any", books=[], total_results=0)

    monkeypatch.setattr(provider, "gutendex_search", lambda query, limit: stub_response("gutendex"))
    monkeypatch.setattr(provider, "openlibrary_search", lambda query, limit: stub_response("openlibrary"))
    monkeypatch.setattr(provider, "standard_ebooks_search", lambda query, limit: stub_response("standard-ebooks"))

    result = await provider.discover_books("any", sources=["gutendex", "openlibrary", "standard"], limit=1)
    assert result["query"] == "any"
    assert len(result["responses"]) == 3

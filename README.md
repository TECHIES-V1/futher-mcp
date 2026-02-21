# Further-MCP

Further-MCP merges the PDF/EPUB processing layer from `ebook-mcp` with the OpenLibrary discovery tools. You get:

- **Book search intelligence** powered by OpenLibrary with keyword-aware query construction.
- **Flexible ebook conversion** – metadata, table of contents, and chapter-level Markdown for EPUB/PDF files.
- **Dual interfaces**: launch as a FastAPI app or a FastMCP pack (Claude/Desktop friendly) without touching another repo.
- **Deploy-ready** for modern hosts (Railway, Render) with `.env`-controlled configuration.

## Quick Start

1. **Install dependencies**
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Prepare environment**
   - Copy `.env.example` to `.env` and set values for:
     - `OPENLIBRARY_BASE_URL` (defaults to `https://openlibrary.org`)
     - `EBOOK_ROOT_PATH` (local folder where EPUB/PDF books live)
     - `LOG_LEVEL` (e.g., `INFO`, `DEBUG`)
   - Drop EPUB/PDF files under the configured `EBOOK_ROOT_PATH`.

3. **Run the FastAPI layer**
   ```bash
   further-mcp-fastapi
   ```
   Defaults to `0.0.0.0:8000`. Use `uvicorn` arguments if you need HTTPS, auto-reload, etc.

4. **Run the FastMCP pack**
   ```bash
   further-mcp
   ```
   This spins up a FastMCP (stdio) server ready for Claude Desktop or other MCP clients.

5. **Run the test suite**
   ```bash
   pytest
   ```

## FastAPI Endpoints

| Path | Method | Description |
| ---- | ------ | ----------- |
| `/search` | GET | Smart OpenLibrary search. Use `keywords` (e.g., `keywords=Python&keywords=Introduction`). |
| `/search_author` | GET | Find author information + works. |
| `/ebooks/list` | GET | List EPUB/PDF files inside the configured root. |
| `/ebooks/metadata` | GET | Returns metadata for a given file. |
| `/ebooks/toc` | GET | Returns TOC for EPUB/PDF. |
| `/ebooks/epub/chapter-markdown` | GET | Get chapter Markdown (`chapter` param). |
| `/ebooks/pdf/chapter-text` | GET | Get text + pages for a PDF chapter title match. |

Use the `/health` endpoint (`GET /health`) to confirm the FastAPI server is alive.

## FastMCP Tools

Register the pack in Claude/Desktop using `further-mcp` (FastMCP) command. Available tools:

- `search_books(query: str, keywords: list[str] | None = None, limit: int = 10) -> OpenLibrary`
- `search_author(query: str) -> AuthorDetails`
- `search_author_with_book_name(query: str) -> AuthorDetails`
- `list_ebooks() -> dict`
- `get_epub_metadata(relative_path: str)`
- `get_pdf_metadata(relative_path: str)`
- `get_epub_toc(relative_path: str)`
- `get_pdf_toc(relative_path: str)`
- `get_epub_chapter_markdown(relative_path: str, chapter_id: str)`
- `get_pdf_chapter_text(relative_path: str, chapter_title: str)`

## `.env` configuration

```env
OPENLIBRARY_BASE_URL=https://openlibrary.org
EBOOK_ROOT_PATH=ebooks
LOG_LEVEL=INFO
```

The FastAPI server and MCP layer both respect the same environment file, so they stay aligned in deployments (Railway/Render) and local dev.

## Packaging for MCPB

The `further-mcp.pack.json` manifest describes this project as a deployable `mcpb` pack. Claude/Desktop or MCP pack managers can point to it when installing the pack.

## Deployment hints

1. **Railway/Render**
   - Point the start command to `python -m further_mcp.fastapi_server` or call `further-mcp-fastapi`.
   - Add `PYTHONPATH=src` if required by your environment.
   - Configure the `.env` variables via the service’s UI.
2. **Logs**
   - Structured logs land in `logs/further_mcp.log`, human readable output shows in stdout/stderr for fast feedback.

## Requirements

- `fastapi >=0.116.0`
- `fastmcp >=2.11.1`
- `uvicorn >=0.24.0`
- `ebooklib >=0.19`
- `PyMuPDF >=1.26.3`
- `beautifulsoup4 >=4.13.4`
- `html2text >=2025.4.15`
- `pydantic >=2.11.7`
- `httpx >=0.28.0`
- `python-dotenv >=1.1.0`

Refer to `requirements.txt` for the pinned versions used in this workspace.

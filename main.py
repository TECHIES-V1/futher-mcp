"""Entrypoint for MCP + HTTP deployments.

Exposes `app` for `uvicorn main:app` (Railway/Render) and preserves
the old `python main.py` behavior for MCP usage.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from further_mcp.fastapi_server import APP as app
from further_mcp.mcp_server import main


if __name__ == "__main__":
    main()

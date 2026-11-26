"""Vercel Python Serverless ASGI Entrypoint for CARAVAN Standalone Platform."""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# Ensure both api directory and backend directory are on sys.path
_API_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _API_DIR.parent / "backend"

for p in (_API_DIR, _BACKEND_DIR):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

_startup_error = None
app = None

try:
    from app.db.session import run_migrations
    try:
        run_migrations()
    except Exception as mig_err:
        sys.stderr.write(f"[CARAVAN] Startup migration notice: {mig_err}\n")
        sys.stderr.flush()

    from app.main import app as _caravan_app
    app = _caravan_app
except Exception as exc:
    _startup_error = {
        "status": "startup_failed",
        "error": "CARAVAN Backend Startup Failed",
        "exception_type": type(exc).__name__,
        "detail": str(exc),
        "traceback": traceback.format_exc(),
        "python_version": sys.version,
        "sys_path": sys.path[:5],
    }
    sys.stderr.write(f"[CARAVAN STARTUP FATAL ERROR]: {exc}\n")
    sys.stderr.write(_startup_error["traceback"])
    sys.stderr.flush()

    async def fallback_diagnostic_app(scope, receive, send):
        if scope["type"] == "http":
            body = json.dumps(_startup_error, indent=2).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"x-caravan-status", b"startup_failure"),
                    (b"access-control-allow-origin", b"*"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
        else:
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": b""})

    app = fallback_diagnostic_app

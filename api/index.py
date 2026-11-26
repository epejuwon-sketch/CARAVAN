"""Vercel Python Serverless ASGI Entrypoint for CARAVAN Standalone Platform."""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# Ensure api and backend directories are on sys.path
_API_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _API_DIR.parent / "backend"

for p in (_API_DIR, _BACKEND_DIR):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

_startup_error = None
_caravan_app = None

try:
    from app.main import app as _caravan_app
except Exception as exc:
    _startup_error = {
        "status": "startup_failed",
        "error": "CARAVAN Backend Startup Failed",
        "exception_type": type(exc).__name__,
        "detail": str(exc),
        "traceback": traceback.format_exc(),
        "python_version": sys.version,
    }
    sys.stderr.write(f"[CARAVAN STARTUP FATAL ERROR]: {exc}\n")
    sys.stderr.write(_startup_error["traceback"])
    sys.stderr.flush()


async def app(scope, receive, send):
    """Universal ASGI handler with compliant lifespan protocol and exception shielding."""
    if scope["type"] == "lifespan":
        # Handle ASGI lifespan protocol correctly for Mangum/Vercel
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                # Let inner app run lifespan if available and initialized
                if _caravan_app is not None:
                    try:
                        # FastAPI lifespan is handled if we delegate, but to avoid Mangum timeout hangs
                        pass
                    except Exception as le:
                        sys.stderr.write(f"[CARAVAN LIFESPAN NOTICE]: {le}\n")
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    elif scope["type"] == "http":
        # If startup failed during module import, return diagnostic payload with HTTP 500
        if _startup_error is not None:
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
            return

        # Delegate request to FastAPI app
        try:
            await _caravan_app(scope, receive, send)
        except Exception as http_exc:
            error_payload = {
                "status": "runtime_error",
                "error": "CARAVAN Unhandled Request Exception",
                "exception_type": type(http_exc).__name__,
                "detail": str(http_exc),
                "traceback": traceback.format_exc(),
            }
            body = json.dumps(error_payload, indent=2).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"x-caravan-status", b"runtime_exception"),
                    (b"access-control-allow-origin", b"*"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
    else:
        # Unknown scope
        if _caravan_app is not None:
            await _caravan_app(scope, receive, send)

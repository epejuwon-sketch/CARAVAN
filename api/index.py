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
    err_msg = str(exc)
    if "JWT_SECRET_KEY" in err_msg:
        _startup_error = "jwt_secret_key_invalid_or_missing"
    elif "DATABASE_URL" in err_msg:
        _startup_error = "database_url_invalid_or_missing"
    elif "ModuleNotFoundError" in type(exc).__name__:
        _startup_error = f"module_not_found:{getattr(exc, 'name', '')}"
    else:
        _startup_error = type(exc).__name__
    sys.stderr.write(f"[CARAVAN STARTUP FATAL ERROR]: {exc}\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.flush()


async def app(scope, receive, send):
    """Universal ASGI handler with compliant lifespan protocol and exception shielding."""
    if scope["type"] == "lifespan":
        # Handle ASGI lifespan protocol correctly for Mangum/Vercel
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    elif scope["type"] == "http":
        # If startup failed during module import, return sanitized error category with HTTP 500
        if _startup_error is not None:
            body = json.dumps({
                "detail": "Application startup in progress or configuration incomplete.",
                "failure_category": _startup_error,
            }).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"x-caravan-status", f"startup_failure:{_startup_error}".encode("utf-8")),
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
            sys.stderr.write(f"[CARAVAN RUNTIME ERROR]: {http_exc}\n{traceback.format_exc()}\n")
            sys.stderr.flush()
            body = json.dumps({
                "detail": "Internal server error. Please retry shortly."
            }).encode("utf-8")
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

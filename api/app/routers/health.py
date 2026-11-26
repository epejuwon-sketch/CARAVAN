"""CARAVAN Standalone Platform — Health Probes & Readiness Routes."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine, get_storage_mode

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
@router.get("/api/v1/health")
def api_health():
    """Production health check.

    Verifies persistent database connectivity via SELECT 1.
    Never exposes credentials, secrets, internal connection strings, or stack traces.
    """
    t0 = time.perf_counter()
    settings = get_settings()

    db_connected = False
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    storage_mode = get_storage_mode()

    res = {
        "status": "ready" if db_connected else "degraded",
        "service": "CARAVAN Funding Intelligence Platform",
        "version": "1.0.0-production",
        "environment": settings.CARAVAN_ENV,
        "database": "connected" if db_connected else "disconnected",
        "storage_mode": storage_mode,
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not db_connected:
        return Response(
            content=json.dumps(res),
            status_code=503,
            media_type="application/json",
        )
    return res

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
    Never exposes credentials, secrets, passwords, or stack traces.
    """
    t0 = time.perf_counter()
    settings = get_settings()

    db_connected = False
    failure_category = None
    target_host = None

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        db_connected = False
        err_msg = str(exc).lower()
        if "password authentication failed" in err_msg:
            failure_category = "password_authentication_failed"
        elif "timeout" in err_msg or "timed out" in err_msg:
            failure_category = "connection_timeout"
        elif "network is unreachable" in err_msg:
            failure_category = "network_unreachable_ipv6"
        elif "could not translate host" in err_msg:
            failure_category = "dns_resolution_failed"
        elif "connection refused" in err_msg:
            failure_category = "connection_refused"
        else:
            failure_category = type(exc).__name__

        from sqlalchemy.engine import make_url
        try:
            from app.db.session import normalize_database_url
            parsed = make_url(normalize_database_url(settings.DATABASE_URL))
            target_host = parsed.host
        except Exception:
            pass

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
        if failure_category:
            res["failure_category"] = failure_category
        if target_host:
            res["target_host"] = target_host
        return Response(
            content=json.dumps(res),
            status_code=503,
            media_type="application/json",
        )
    return res

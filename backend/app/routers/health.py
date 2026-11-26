"""CARAVAN Standalone Platform — Health Probes & Readiness Routes."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
@router.get("/api/v1/health")
def api_health(db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    db_healthy = True
    db_err_detail = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_healthy = False
        db_err_detail = f"{type(exc).__name__}: {exc}"
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    from app.core.config import get_settings
    from app.db.session import normalize_database_url
    from sqlalchemy.engine import make_url

    settings = get_settings()
    norm_url = normalize_database_url(settings.DATABASE_URL)
    sanitized_url = "unknown"
    try:
        parsed = make_url(norm_url)
        sanitized_url = parsed.render_as_string(hide_password=True)
    except Exception:
        sanitized_url = norm_url.split("@")[-1] if "@" in norm_url else norm_url[:12]

    res = {
        "status": "ready" if db_healthy else "degraded",
        "service": "CARAVAN Funding Intelligence Platform",
        "version": "1.0.0-production",
        "environment": "production",
        "database": "healthy" if db_healthy else "disconnected",
        "database_target": sanitized_url,
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not db_healthy:
        res["database_diagnostic"] = db_err_detail
    return res

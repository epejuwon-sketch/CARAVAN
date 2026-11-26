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
    from app.db.session import normalize_database_url, is_using_fallback, get_primary_db_error
    from sqlalchemy.engine import make_url

    settings = get_settings()
    norm_url = normalize_database_url(settings.DATABASE_URL)
    sanitized_url = "unknown"
    try:
        parsed = make_url(norm_url)
        sanitized_url = parsed.render_as_string(hide_password=True)
    except Exception:
        pass

    using_fallback = is_using_fallback()
    primary_err = get_primary_db_error()

    res = {
        "status": "ready" if db_healthy else "degraded",
        "service": "CARAVAN Funding Intelligence Platform",
        "version": "1.0.0-production",
        "environment": "production",
        "database": "healthy" if db_healthy and not using_fallback else ("healthy_resilient_failover" if db_healthy else "disconnected"),
        "storage_mode": "primary_postgres" if not using_fallback else "serverless_sqlite_failover",
        "database_target": sanitized_url if not using_fallback else "/tmp/caravan.db",
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if using_fallback:
        res["primary_database_target"] = sanitized_url
        res["primary_database_diagnostic"] = primary_err
        res["failover_notice"] = (
            "Primary database connection failed. Running continuously on resilient serverless SQLite storage. "
            "Update DATABASE_URL in Vercel to restore PostgreSQL synchronization."
        )
    if not db_healthy:
        res["database_diagnostic"] = db_err_detail
    return res

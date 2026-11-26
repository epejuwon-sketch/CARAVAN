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

        # Check port 6543 alternative for Supabase pooler
        if "pooler.supabase.com" in norm_url and ":5432" in norm_url:
            from sqlalchemy import create_engine as ce
            try:
                url_6543 = norm_url.replace(":5432", ":6543")
                eng_6543 = ce(url_6543, connect_args={"connect_timeout": 3})
                with eng_6543.connect() as conn:
                    conn.execute(text("SELECT 1"))
                res["supabase_port_6543_test"] = "SUCCESS"
            except Exception as e6543:
                res["supabase_port_6543_test"] = f"{type(e6543).__name__}: {e6543}"

        try:
            raw_pw = parsed.password or ""
            res["password_metadata"] = {
                "length": len(raw_pw),
                "has_special_chars": any(c in raw_pw for c in "@#%&:/?$"),
                "is_ascii": raw_pw.isascii(),
            }
        except Exception:
            pass
    return res

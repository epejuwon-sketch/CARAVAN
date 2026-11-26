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
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "status": "ready" if db_healthy else "degraded",
        "service": "CARAVAN Funding Intelligence Platform",
        "version": "1.0.0-production",
        "environment": "production",
        "database": "healthy" if db_healthy else "disconnected",
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

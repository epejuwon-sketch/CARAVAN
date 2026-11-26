"""CARAVAN Standalone Platform — Automated Cron Execution Endpoints."""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.discovery_service import DailyDiscoveryScheduler, DiscoveryEngine

logger = logging.getLogger("caravan")

router = APIRouter(prefix="/api/v1/cron", tags=["Scheduled Automated Jobs"])


def verify_cron_access(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_vercel_cron: Optional[str] = Header(None, alias="x-vercel-cron"),
    secret: Optional[str] = Query(None),
) -> bool:
    """Validate that the cron request originated from Vercel Scheduler or authorized administrator."""
    settings = get_settings()
    configured_secret = (settings.CRON_SECRET or "").strip()

    # If a CRON_SECRET is configured, strictly enforce bearer token or query secret
    if configured_secret:
        auth_token = None
        if authorization and authorization.lower().startswith("bearer "):
            auth_token = authorization.split(" ", 1)[1].strip()
        elif secret:
            auth_token = secret.strip()

        if auth_token != configured_secret:
            logger.warning("Unauthorized cron invocation attempt. Invalid or missing secret.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized cron trigger. Provide valid Authorization Bearer token.",
            )
    else:
        # Development / staging fallback: permit execution with a notice in logs
        logger.info("CRON_SECRET not configured; permitting invocation under development policy.")

    return True


@router.get("/discovery")
@router.post("/discovery")
def trigger_daily_discovery_cron(
    authorized: bool = Depends(verify_cron_access),
    db: Session = Depends(get_db),
):
    """Trigger the autonomous daily institutional funding discovery cycle."""
    logger.info("Initiating autonomous daily funding discovery cycle via cron trigger...")
    try:
        results = DailyDiscoveryScheduler.execute_daily_cycle(db, actor="CRON:VERCEL_DAILY_DISCOVERY")
        return {
            "status": "COMPLETED",
            "job": "AUTONOMOUS_DAILY_FUNDING_DISCOVERY",
            "summary": results,
        }
    except Exception as exc:
        logger.error("Daily discovery cron cycle failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily discovery cycle failed: {str(exc)}",
        )


@router.get("/monitoring")
@router.post("/monitoring")
def trigger_continuous_monitoring_cron(
    authorized: bool = Depends(verify_cron_access),
    db: Session = Depends(get_db),
):
    """Trigger continuous lifecycle monitoring: status recalibration and deadline approaching alerts."""
    logger.info("Initiating continuous lifecycle monitoring cycle via cron trigger...")
    try:
        results = DiscoveryEngine.monitor_continuous_lifecycle(db, actor="CRON:CONTINUOUS_MONITOR")
        return {
            "status": "COMPLETED",
            "job": "CONTINUOUS_LIFECYCLE_MONITORING",
            "summary": results,
        }
    except Exception as exc:
        logger.error("Continuous lifecycle monitoring failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Continuous lifecycle monitoring failed: {str(exc)}",
        )


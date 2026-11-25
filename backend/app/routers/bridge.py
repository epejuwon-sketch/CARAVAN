"""CARAVAN Standalone Platform — Scoped S2S Bridge for ULTRON Operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, verify_ultron_bridge
from app.services.bridge_service import get_caravan_operations_telemetry, execute_bridge_sweep_expired

router = APIRouter(prefix="/api/v1/bridge", tags=["ULTRON Operations Bridge"])


@router.get("/telemetry")
def api_bridge_telemetry(
    principal: CaravanPrincipal = Depends(verify_ultron_bridge),
    db: Session = Depends(get_db),
):
    """Secure S2S endpoint providing real-time telemetry to ULTRON CARAVAN Operations."""
    return get_caravan_operations_telemetry(db)


@router.post("/sweep-expired")
def api_bridge_sweep_expired(
    principal: CaravanPrincipal = Depends(verify_ultron_bridge),
    db: Session = Depends(get_db),
):
    """Scoped S2S action allowing ULTRON Operations to sweep expired funding opportunities."""
    return execute_bridge_sweep_expired(db)

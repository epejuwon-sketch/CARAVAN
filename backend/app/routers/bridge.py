"""CARAVAN Standalone Platform — Scoped S2S Bridge for ULTRON Operations."""

from __future__ import annotations

from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, verify_ultron_bridge
from app.services.bridge_service import (
    get_caravan_operations_telemetry,
    execute_bridge_sweep_expired,
    execute_caravan_agent_action,
)

router = APIRouter(prefix="/api/v1/bridge", tags=["ULTRON Operations Bridge"])


class CaravanAgentActionRequest(BaseModel):
    operation: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    scope: Optional[str] = None
    correlation_id: Optional[str] = None
    task_id: Optional[str] = None


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


@router.post("/opportunities")
def api_bridge_ingest_candidate(
    candidate: dict,
    principal: CaravanPrincipal = Depends(verify_ultron_bridge),
    db: Session = Depends(get_db),
):
    """Scoped S2S endpoint allowing ULTRON Sentinel Sub-Agent to ingest candidate funding opportunities into the review queue."""
    from app.services.discovery_service import DiscoveryEngine
    return DiscoveryEngine.ingest_discovered_opportunity(db, candidate, discovered_by="ULTRON_SENTINEL_SUBAGENT")


@router.post("/agent-action")
def api_bridge_agent_action(
    payload: CaravanAgentActionRequest,
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-ID"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
    x_task_id: Optional[str] = Header(None, alias="X-Task-ID"),
    principal: CaravanPrincipal = Depends(verify_ultron_bridge),
    db: Session = Depends(get_db),
):
    """Execute a scoped 60-agent action across the 12 CARAVAN functional domains."""
    agent_id = x_agent_id or payload.agent_id
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required agent identifier (X-Agent-ID header or agent_id in request body).",
        )

    correlation_id = x_correlation_id or payload.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    task_id = x_task_id or payload.task_id
    scope = payload.scope

    try:
        return execute_caravan_agent_action(
            db,
            agent_id=agent_id,
            operation=payload.operation,
            parameters=payload.parameters,
            correlation_id=correlation_id,
            scope=scope,
            task_id=task_id,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent action execution failed: {str(e)}",
        )


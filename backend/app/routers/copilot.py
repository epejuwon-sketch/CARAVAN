"""CARAVAN Standalone Platform — Business Copilot & AI Advisory Router."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import OrganizationRecord
from app.core.permissions import CaravanPrincipal, get_current_principal
from app.services.copilot_service import (
    CopilotEngine,
    calculate_business_readiness,
)

router = APIRouter(prefix="/api/v1/copilot", tags=["CARAVAN Business Copilot"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Funding Strategy Consultation"
    context_mode: Optional[str] = "GENERAL"
    target_id: Optional[str] = None


class ChatMessageRequest(BaseModel):
    message: str


class DraftProposalRequest(BaseModel):
    opportunity_id: str


@router.get("/sessions")
def api_list_copilot_sessions(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """List conversation threads for the authenticated organization."""
    return {"sessions": CopilotEngine.list_sessions(db, org_id=principal.organization_id)}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def api_create_copilot_session(
    body: CreateSessionRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Create a new conversational workspace thread."""
    sess = CopilotEngine.get_or_create_session(
        db,
        org_id=principal.organization_id,
        user_id=principal.user_id,
        context_mode=body.context_mode or "GENERAL",
        target_id=body.target_id,
    )
    return {
        "session_id": sess.session_id,
        "title": sess.title,
        "context_mode": sess.context_mode,
        "target_id": sess.target_id,
        "created_at": sess.created_at.isoformat(),
    }


@router.get("/sessions/{session_id}/messages")
def api_get_session_messages(
    session_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Retrieve message history for a specific thread."""
    messages = CopilotEngine.get_session_messages(db, org_id=principal.organization_id, session_id=session_id)
    return {"session_id": session_id, "messages": messages}


@router.post("/sessions/{session_id}/chat")
def api_send_copilot_message(
    session_id: str,
    body: ChatMessageRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Send user query to the AI Business Copilot and receive grounded response."""
    if not body.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty.")

    return CopilotEngine.generate_copilot_response(
        db,
        org_id=principal.organization_id,
        user_id=principal.user_id,
        session_id=session_id,
        user_message=body.message,
    )


@router.get("/readiness-report")
def api_get_readiness_report(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Generate structured business funding readiness diagnostic report."""
    org = db.execute(
        select(OrganizationRecord).where(OrganizationRecord.org_id == principal.organization_id)
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization record not found.")

    readiness = calculate_business_readiness(org)
    return {
        "organization_id": org.org_id,
        "organization_name": org.name,
        "sector": org.sector,
        "stage": org.stage,
        "readiness": readiness,
    }


@router.post("/draft-proposal")
def api_draft_proposal(
    body: DraftProposalRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Generate structured proposal draft for a specific funding opportunity."""
    return CopilotEngine.draft_proposal_for_opportunity(
        db,
        org_id=principal.organization_id,
        opportunity_id=body.opportunity_id,
    )

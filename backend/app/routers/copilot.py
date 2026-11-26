"""CARAVAN Standalone Platform — Business Copilot & AI Advisory Router.

Exposes endpoints for:
- Conversational Copilot sessions and multi-turn chat
- Business funding readiness diagnostics
- 13-step Grant Application Agent drafting, approval gating, and submission
- Document readiness audits
- Voice interaction capabilities, transcription, and speech synthesis
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
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
from app.services.application_agent import ApplicationAgent
from app.services.document_intelligence import DocumentIntelligence
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/api/v1/copilot", tags=["CARAVAN Business Copilot"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Funding Strategy Consultation"
    context_mode: Optional[str] = "GENERAL"
    target_id: Optional[str] = None


class ChatMessageRequest(BaseModel):
    message: str


class DraftProposalRequest(BaseModel):
    opportunity_id: str
    application_id: Optional[str] = None


class ApproveApplicationRequest(BaseModel):
    application_id: str
    customer_notes: Optional[str] = ""


class AdminOverrideRequest(BaseModel):
    application_id: str
    override_reason: str
    exception_notes: Optional[str] = ""
    target_org_id: Optional[str] = None


class ConfirmExtractedFieldsRequest(BaseModel):
    confirmed_fields: Dict[str, Any]


class SubmitApplicationRequest(BaseModel):
    application_id: str
    approval_id: str


class VoiceSynthesizeRequest(BaseModel):
    text: str
    voice_profile: Optional[str] = "CARAVAN_ADVISOR"


class UpdateProfileFieldsRequest(BaseModel):
    fields: Dict[str, Any]


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


# 13-Step Application Agent Endpoints
@router.post("/application-agent/draft", status_code=status.HTTP_201_CREATED)
def api_application_agent_draft(
    body: DraftProposalRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Execute Steps 1-10: Evaluate opportunity, audit documents, draft validated answers."""
    try:
        return ApplicationAgent.draft_application_workflow(
            db=db,
            org_id=principal.organization_id,
            opportunity_id=body.opportunity_id,
            application_id=body.application_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Draft application notice: {type(exc).__name__}: {exc}",
        )


@router.get("/ai-status")
def api_copilot_ai_status():
    """Diagnostic endpoint reporting real AI Intelligence Provider configuration and status."""
    from app.services.ai_provider import AIProviderFactory
    from app.services.ocr_service import OCRProviderFactory

    status_data = AIProviderFactory.get_status()
    ocr_caps = OCRProviderFactory.get_ocr_capabilities()
    status_data["ocr_status"] = ocr_caps["ocr_status"]
    status_data["ocr_available"] = ocr_caps["ocr_status"] == "READY"
    status_data["ocr_engine"] = ocr_caps["active_engine"]
    status_data["ocr_capabilities"] = ocr_caps
    status_data["voice_transcription_ready"] = True
    status_data["voice_synthesis_ready"] = True
    return status_data


@router.get("/ai-diagnostics")
def api_copilot_ai_diagnostics():
    """Detailed diagnostics of model endpoints and capabilities without exposing secrets."""
    from app.services.ai_provider import AIProviderFactory
    return AIProviderFactory.diagnose_gemini()


@router.post("/application-agent/approve", status_code=status.HTTP_200_OK)
def api_application_agent_approve(
    body: ApproveApplicationRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Step 11: Explicit Customer Approval. Rejects INCOMPLETE applications with HTTP 422."""
    return ApplicationAgent.approve_application_workflow(
        db=db,
        org_id=principal.organization_id,
        user_id=principal.user_id,
        application_id=body.application_id,
        customer_notes=body.customer_notes or "",
    )


@router.post("/application-agent/admin-override", status_code=status.HTTP_200_OK)
def api_application_agent_admin_override(
    body: AdminOverrideRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Explicit Administrator Exception Override. Requires PLATFORM_ADMIN, SUPER_ADMIN, or ADMIN role."""
    target_org = body.target_org_id or principal.organization_id
    return ApplicationAgent.admin_override_workflow(
        db=db,
        admin_principal=principal,
        target_org_id=target_org,
        application_id=body.application_id,
        override_reason=body.override_reason,
        exception_notes=body.exception_notes or "",
    )


@router.post("/documents/{document_id}/confirm-fields", status_code=status.HTTP_200_OK)
def api_confirm_document_fields(
    document_id: str,
    body: ConfirmExtractedFieldsRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Customer confirmation or correction of uncertain OCR-extracted fields."""
    from app.db.models import DocumentMetadataRecord, AuditLogRecord, gen_id
    doc = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.doc_id == document_id,
            DocumentMetadataRecord.organization_id == principal.organization_id,
            DocumentMetadataRecord.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    audit = AuditLogRecord(
        log_id=gen_id("aud"),
        actor=principal.user_id,
        action="DOCUMENT_EXTRACTED_FIELDS_CONFIRMED_BY_CUSTOMER",
        resource=f"DOCUMENT:{document_id}",
        outcome="SUCCESS",
        details={"organization_id": principal.organization_id, "confirmed_fields": body.confirmed_fields},
    )
    db.add(audit)
    db.commit()
    return {
        "status": "CONFIRMED",
        "document_id": document_id,
        "confirmed_fields": body.confirmed_fields,
        "message": "Extracted fields confirmed by customer.",
    }


@router.post("/application-agent/submit", status_code=status.HTTP_200_OK)
def api_application_agent_submit(
    body: SubmitApplicationRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Steps 12 & 13: Submission with explicit customer approval gating."""
    return ApplicationAgent.submit_application_workflow(
        db=db,
        org_id=principal.organization_id,
        user_id=principal.user_id,
        application_id=body.application_id,
        approval_id=body.approval_id,
    )


# Document Readiness Audit Endpoint
@router.get("/document-readiness/{opportunity_id}")
def api_document_readiness(
    opportunity_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Audits customer's private vault documents against an opportunity's requirement checklist."""
    return DocumentIntelligence.match_documents_to_requirements(
        db=db,
        org_id=principal.organization_id,
        opportunity_id=opportunity_id,
    )


# Voice Capabilities Endpoints
@router.get("/voice/capabilities")
def api_voice_capabilities():
    """Returns supported voice modes, speech-to-text codecs, and synthesis options."""
    return VoiceService.get_voice_capabilities()


@router.post("/voice/synthesize")
def api_voice_synthesize(body: VoiceSynthesizeRequest):
    """Synthesizes text content into speech metadata for client-side or audio playback."""
    return VoiceService.synthesize_speech(text=body.text, voice_profile=body.voice_profile or "CARAVAN_ADVISOR")


@router.post("/voice/transcribe")
async def api_voice_transcribe(
    file: UploadFile = File(...),
    locale: str = Form("en-NG"),
    principal: CaravanPrincipal = Depends(get_current_principal),
):
    """Speech-to-text transcription hook for voice queries."""
    audio_bytes = await file.read()
    return VoiceService.transcribe_audio_buffer(
        audio_bytes=audio_bytes,
        content_type=file.content_type or "audio/webm",
        locale=locale,
    )


# AURELIA 8-Stage Customer Journey Endpoints
@router.get("/journey/{opportunity_id}")
def api_get_customer_journey(
    opportunity_id: str,
    application_id: Optional[str] = None,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Returns the complete 8-stage AURELIA customer funding journey:
    DISCOVER -> MATCH -> UNDERSTAND -> PREPARE -> REVIEW -> APPROVE -> SUBMIT -> TRACK.
    """
    try:
        return ApplicationAgent.get_customer_journey(
            db=db,
            org_id=principal.organization_id,
            opportunity_id=opportunity_id,
            application_id=application_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Customer journey calculation notice: {type(exc).__name__}: {exc}",
        )


@router.post("/journey/{opportunity_id}/update-profile")
def api_update_journey_profile(
    opportunity_id: str,
    body: UpdateProfileFieldsRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Allows customer to provide missing business details directly via AURELIA to advance journey."""
    try:
        return ApplicationAgent.update_missing_business_info(
            db=db,
            org_id=principal.organization_id,
            user_id=principal.user_id,
            fields=body.fields,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update profile notice: {type(exc).__name__}: {exc}",
        )

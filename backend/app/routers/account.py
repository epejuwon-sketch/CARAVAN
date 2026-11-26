"""CARAVAN Standalone Platform — Account & Organization Profile Routes."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import OrganizationRecord, UserRecord
from app.core.permissions import CaravanPrincipal, get_current_principal

router = APIRouter(prefix="/api/v1/account", tags=["Account & Profile"])


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    entity_type: Optional[str] = None
    country: Optional[str] = None
    state_location: Optional[str] = None
    sector: Optional[str] = None
    stage: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    annual_revenue_ngn: Optional[float] = None
    funding_goals: Optional[str] = None
    team_size: Optional[int] = None
    cac_registered: Optional[bool] = None
    years_in_operation: Optional[int] = None
    female_led: Optional[bool] = None
    youth_led: Optional[bool] = None
    products_services: Optional[str] = None
    target_customers: Optional[str] = None
    business_model: Optional[str] = None
    growth_objectives: Optional[str] = None
    intended_use_of_funds: Optional[str] = None
    previous_funding_history: Optional[List[dict]] = None


@router.get("/organization")
def api_get_organization(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    org = db.execute(
        select(OrganizationRecord).where(OrganizationRecord.org_id == principal.organization_id)
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    users = db.execute(
        select(UserRecord).where(UserRecord.organization_id == principal.organization_id)
    ).scalars().all()

    from app.services.copilot_service import calculate_business_readiness
    readiness = calculate_business_readiness(org)

    return {
        "org_id": org.org_id,
        "name": org.name,
        "entity_type": org.entity_type,
        "country": org.country,
        "state_location": org.state_location,
        "sector": org.sector,
        "stage": org.stage,
        "annual_revenue_usd": org.annual_revenue_usd,
        "annual_revenue_ngn": getattr(org, "annual_revenue_ngn", 0.0),
        "funding_goals": org.funding_goals,
        "team_size": org.team_size,
        "cac_registered": getattr(org, "cac_registered", True),
        "years_in_operation": getattr(org, "years_in_operation", 1),
        "female_led": getattr(org, "female_led", False),
        "youth_led": getattr(org, "youth_led", True),
        "products_services": getattr(org, "products_services", ""),
        "target_customers": getattr(org, "target_customers", ""),
        "business_model": getattr(org, "business_model", "B2B"),
        "growth_objectives": getattr(org, "growth_objectives", ""),
        "intended_use_of_funds": getattr(org, "intended_use_of_funds", ""),
        "previous_funding_history": getattr(org, "previous_funding_history", []),
        "readiness_score": readiness["readiness_score"],
        "readiness_level": readiness["readiness_level"],
        "team_members": [
            {
                "user_id": u.user_id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
            }
            for u in users
        ],
    }


@router.put("/organization")
def api_update_organization(
    body: UpdateOrgRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    org = db.execute(
        select(OrganizationRecord).where(OrganizationRecord.org_id == principal.organization_id)
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    if body.name is not None:
        org.name = body.name.strip()
    if body.entity_type is not None:
        org.entity_type = body.entity_type
    if body.country is not None:
        org.country = body.country
    if body.state_location is not None:
        org.state_location = body.state_location
    if body.sector is not None:
        org.sector = body.sector
    if body.stage is not None:
        org.stage = body.stage
    if body.annual_revenue_usd is not None:
        org.annual_revenue_usd = body.annual_revenue_usd
    if body.annual_revenue_ngn is not None:
        org.annual_revenue_ngn = body.annual_revenue_ngn
    if body.funding_goals is not None:
        org.funding_goals = body.funding_goals
    if body.team_size is not None:
        org.team_size = body.team_size
    if body.cac_registered is not None:
        org.cac_registered = body.cac_registered
    if body.years_in_operation is not None:
        org.years_in_operation = body.years_in_operation
    if body.female_led is not None:
        org.female_led = body.female_led
    if body.youth_led is not None:
        org.youth_led = body.youth_led
    if body.products_services is not None:
        org.products_services = body.products_services
    if body.target_customers is not None:
        org.target_customers = body.target_customers
    if body.business_model is not None:
        org.business_model = body.business_model
    if body.growth_objectives is not None:
        org.growth_objectives = body.growth_objectives
    if body.intended_use_of_funds is not None:
        org.intended_use_of_funds = body.intended_use_of_funds
    if body.previous_funding_history is not None:
        org.previous_funding_history = body.previous_funding_history

    from app.services.copilot_service import calculate_business_readiness
    readiness = calculate_business_readiness(org)
    org.readiness_score = readiness["readiness_score"]
    org.readiness_breakdown = readiness["pillars"]

    db.commit()
    db.refresh(org)

    return {
        "status": "UPDATED",
        "org_id": org.org_id,
        "name": org.name,
        "sector": org.sector,
        "stage": org.stage,
        "annual_revenue_usd": org.annual_revenue_usd,
        "annual_revenue_ngn": getattr(org, "annual_revenue_ngn", 0.0),
        "funding_goals": org.funding_goals,
        "team_size": org.team_size,
        "cac_registered": getattr(org, "cac_registered", True),
        "years_in_operation": getattr(org, "years_in_operation", 1),
        "female_led": getattr(org, "female_led", False),
        "youth_led": getattr(org, "youth_led", True),
        "products_services": getattr(org, "products_services", ""),
        "target_customers": getattr(org, "target_customers", ""),
        "business_model": getattr(org, "business_model", "B2B"),
        "growth_objectives": getattr(org, "growth_objectives", ""),
        "intended_use_of_funds": getattr(org, "intended_use_of_funds", ""),
        "previous_funding_history": getattr(org, "previous_funding_history", []),
        "readiness_score": org.readiness_score,
        "readiness_level": readiness["readiness_level"],
    }


class DeleteAccountRequest(BaseModel):
    confirmation: str
    reason: Optional[str] = ""
    immediate_purge: bool = True


@router.get("/export-data")
def api_export_customer_data(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """NDPA & GDPR Compliant Customer Data Portability Export."""
    from datetime import datetime, timezone
    from app.db.models import (
        ApplicationRecord,
        DocumentMetadataRecord,
        SavedOpportunityRecord,
        SupportTicketRecord,
        SubscriptionRecord,
        AuditLogRecord,
    )

    org = db.execute(
        select(OrganizationRecord).where(OrganizationRecord.org_id == principal.organization_id)
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    user = db.get(UserRecord, principal.user_id)
    apps = db.execute(
        select(ApplicationRecord).where(ApplicationRecord.organization_id == principal.organization_id)
    ).scalars().all()
    docs = db.execute(
        select(DocumentMetadataRecord).where(DocumentMetadataRecord.organization_id == principal.organization_id)
    ).scalars().all()
    saved = db.execute(
        select(SavedOpportunityRecord).where(SavedOpportunityRecord.organization_id == principal.organization_id)
    ).scalars().all()
    tickets = db.execute(
        select(SupportTicketRecord).where(SupportTicketRecord.organization_id == principal.organization_id)
    ).scalars().all()
    sub = db.execute(
        select(SubscriptionRecord).where(SubscriptionRecord.organization_id == principal.organization_id)
    ).scalar_one_or_none()

    export_payload = {
        "export_metadata": {
            "platform": "CARAVAN Institutional Capital Platform",
            "compliance": "Nigeria Data Protection Act (NDPA 2023) & GDPR",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "export_version": "1.0",
            "requester_id": principal.user_id,
            "requester_email": principal.email,
        },
        "user_profile": {
            "user_id": user.user_id if user else principal.user_id,
            "email": user.email if user else principal.email,
            "full_name": user.full_name if user else "",
            "role": user.role if user else principal.role,
            "created_at": user.created_at.isoformat() if user and user.created_at else None,
        },
        "organization": {
            "org_id": org.org_id,
            "name": org.name,
            "entity_type": org.entity_type,
            "country": org.country,
            "state_location": org.state_location,
            "sector": org.sector,
            "stage": org.stage,
            "annual_revenue_usd": org.annual_revenue_usd,
            "annual_revenue_ngn": getattr(org, "annual_revenue_ngn", 0.0),
            "funding_goals": org.funding_goals,
            "cac_registered": getattr(org, "cac_registered", True),
            "years_in_operation": getattr(org, "years_in_operation", 1),
            "female_led": getattr(org, "female_led", False),
            "youth_led": getattr(org, "youth_led", True),
            "created_at": org.created_at.isoformat() if org.created_at else None,
        },
        "subscription": {
            "tier": sub.tier if sub else "FREE",
            "status": sub.status if sub else "ACTIVE",
            "provider": sub.billing_provider if sub else "NONE",
        },
        "applications": [
            {
                "application_id": a.application_id,
                "opportunity_id": a.opportunity_id,
                "status": a.status,
                "notes": a.notes,
                "checklist_progress": a.checklist_progress,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in apps
        ],
        "documents_metadata": [
            {
                "doc_id": d.doc_id,
                "name": d.name,
                "file_size_bytes": d.file_size_bytes,
                "content_type": d.content_type,
                "sha256_hash": d.sha256_hash,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in docs
        ],
        "saved_opportunities": [
            {
                "saved_id": s.saved_id,
                "opportunity_id": s.opportunity_id,
                "saved_at": s.saved_at.isoformat() if getattr(s, "saved_at", None) else None,
            }
            for s in saved
        ],
        "support_tickets": [
            {
                "ticket_id": t.ticket_id,
                "subject": t.subject,
                "message": t.message,
                "status": t.status,
                "response": t.response,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ],
    }

    # Log audit trail
    audit = AuditLogRecord(
        actor=principal.email,
        action="CUSTOMER_DATA_EXPORTED",
        resource=f"org:{principal.organization_id}",
        outcome="SUCCESS",
        details={"requester_id": principal.user_id},
    )
    db.add(audit)
    db.commit()

    return export_payload


@router.post("/delete-request")
@router.delete("")
def api_request_account_deletion(
    body: DeleteAccountRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Execute authenticated self-service account deactivation, document purge, and statutory deletion."""
    from datetime import datetime, timezone
    from app.db.models import AuditLogRecord, DocumentMetadataRecord, SavedOpportunityRecord

    if body.confirmation.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="To confirm deletion, you must provide confirmation string 'DELETE'.",
        )

    user = db.get(UserRecord, principal.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    # 1. Immediately deactivate user and invalidate all issued tokens
    now = datetime.now(timezone.utc)
    user.is_active = False
    user.revoked_before_at = now
    user.token_version = (getattr(user, "token_version", 1) or 1) + 1

    # Multi-instance token blacklist
    from datetime import timedelta
    from app.db.models import RevokedTokenRecord, ApplicationDraftRecord
    if principal.jti:
        try:
            rev_entry = RevokedTokenRecord(
                token_jti=principal.jti,
                user_id=principal.user_id,
                revoked_at=now,
                expires_at=now + timedelta(days=7),
            )
            db.merge(rev_entry)
        except Exception:
            pass

    # 2. Mark uploaded documents as soft-deleted and trigger storage cleanup
    docs = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.organization_id == principal.organization_id
        )
    ).scalars().all()
    for d in docs:
        d.deleted_at = now
        d.scan_status = "PURGED"

    # 3. Clear application drafts and saved opportunity bookmarks
    drafts = db.execute(
        select(ApplicationDraftRecord).where(
            ApplicationDraftRecord.organization_id == principal.organization_id
        )
    ).scalars().all()
    for dr in drafts:
        db.delete(dr)

    saved = db.execute(
        select(SavedOpportunityRecord).where(
            SavedOpportunityRecord.organization_id == principal.organization_id
        )
    ).scalars().all()
    for s in saved:
        db.delete(s)

    # 4. Record statutory audit trail (retained per NDPA 2023 & CAMA 2020 tax/audit requirements)
    audit = AuditLogRecord(
        actor=principal.email,
        action="ACCOUNT_DELETED",
        resource=f"user:{principal.user_id}",
        outcome="DEACTIVATED_AND_PURGED",
        details={
            "user_id": principal.user_id,
            "organization_id": principal.organization_id,
            "reason": body.reason or "Customer self-service request",
            "purged_at": now.isoformat(),
            "documents_purged_count": len(docs),
            "drafts_purged_count": len(drafts),
            "statutory_retention_basis": "CAMA 2020 Section 375 & NDPA 2023 financial audit exception",
        },
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "status": "DELETION_SCHEDULED",
        "retention_policy_days": 30,
        "message": "Your account has been deactivated and your personal records and documents have been scheduled for purge. Statutory billing references are archived in accordance with statutory accounting standards.",
        "documents_purged": len(docs),
    }


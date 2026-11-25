"""CARAVAN Standalone Platform — Admin Operations & RBAC-Protected Telemetry."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, require_permission
from app.db.models import (
    UserRecord,
    OrganizationRecord,
    FundingOpportunityRecord,
    ApplicationRecord,
    AuditLogRecord,
    utcnow,
)
from app.services.discovery_service import DiscoveryEngine

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Operations"])


class ReviewDecisionRequest(BaseModel):
    notes: Optional[str] = ""
    reason: Optional[str] = ""


class IngestOpportunityRequest(BaseModel):
    title: str
    provider: str
    official_source_url: str
    funding_type: str = "GRANT"
    amount_min: float = 0.0
    amount_max: float = 0.0
    currency: str = "USD"
    amount_display: str = "Amount varies"
    geographic_eligibility: str = "Nigeria / West Africa"
    applicant_eligibility: str = "Registered business entity"
    industry_sector: str = "Multi-Sector"
    application_requirements: List[str] = Field(default_factory=list)
    is_rolling: bool = False
    source_name: str = "Manual Admin Staging"
    verification_evidence: Optional[Dict[str, Any]] = None


class UpdateUserRoleRequest(BaseModel):
    role: str


@router.get("/telemetry")
def api_admin_telemetry(
    principal: CaravanPrincipal = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db),
):
    """Return platform telemetry and operational records, protected by admin:read RBAC."""
    total_users = db.query(func.count(UserRecord.user_id)).scalar() or 0
    total_orgs = db.query(func.count(OrganizationRecord.org_id)).scalar() or 0
    total_apps = db.query(func.count(ApplicationRecord.application_id)).scalar() or 0
    total_opps = (
        db.query(func.count(FundingOpportunityRecord.opportunity_id))
        .filter(FundingOpportunityRecord.verification_status.in_(["VERIFIED", "VERIFIED_OPEN"]))
        .scalar()
        or 0
    )
    pending_queue_count = (
        db.query(func.count(FundingOpportunityRecord.opportunity_id))
        .filter(FundingOpportunityRecord.publication_status == "PENDING_REVIEW")
        .scalar()
        or 0
    )

    # Fetch real applications across organizations
    apps_query = (
        db.query(
            ApplicationRecord.application_id,
            ApplicationRecord.organization_id,
            ApplicationRecord.opportunity_id,
            ApplicationRecord.status,
            ApplicationRecord.created_at,
            ApplicationRecord.notes,
            FundingOpportunityRecord.title.label("opportunity_title"),
            FundingOpportunityRecord.amount_display.label("amount_display"),
            FundingOpportunityRecord.provider.label("provider"),
            OrganizationRecord.name.label("organization_name"),
        )
        .join(FundingOpportunityRecord, ApplicationRecord.opportunity_id == FundingOpportunityRecord.opportunity_id)
        .join(OrganizationRecord, ApplicationRecord.organization_id == OrganizationRecord.org_id)
        .order_by(ApplicationRecord.created_at.desc())
        .limit(20)
        .all()
    )

    recent_apps = [
        {
            "application_id": a.application_id,
            "organization_id": a.organization_id,
            "organization_name": a.organization_name,
            "opportunity_id": a.opportunity_id,
            "opportunity_title": a.opportunity_title,
            "amount_display": a.amount_display,
            "provider": a.provider,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "notes": a.notes,
        }
        for a in apps_query
    ]

    # Fetch real registered users
    users_query = (
        db.query(
            UserRecord.user_id,
            UserRecord.email,
            UserRecord.full_name,
            UserRecord.role,
            UserRecord.is_active,
            UserRecord.created_at,
            OrganizationRecord.name.label("organization_name"),
        )
        .outerjoin(OrganizationRecord, UserRecord.organization_id == OrganizationRecord.org_id)
        .order_by(UserRecord.created_at.desc())
        .limit(50)
        .all()
    )

    users_list = [
        {
            "user_id": u.user_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "organization_name": u.organization_name or "N/A",
        }
        for u in users_query
    ]

    return {
        "total_users": total_users,
        "total_organizations": total_orgs,
        "total_applications": total_apps,
        "total_opportunities": total_opps,
        "pending_review_count": pending_queue_count,
        "applications": recent_apps,
        "users": users_list,
    }


@router.get("/opportunities/queue")
def api_get_opportunity_queue(
    limit: int = 50,
    offset: int = 0,
    principal: CaravanPrincipal = Depends(require_permission("opportunities:review")),
    db: Session = Depends(get_db),
):
    """Retrieve items from the discovery review queue."""
    items = DiscoveryEngine.get_review_queue(db, limit=limit, offset=offset)
    return {"total": len(items), "queue": items}


@router.post("/opportunities/ingest")
def api_ingest_opportunity(
    body: IngestOpportunityRequest,
    principal: CaravanPrincipal = Depends(require_permission("opportunities:write")),
    db: Session = Depends(get_db),
):
    """Ingest a candidate opportunity into the review queue."""
    payload = body.dict()
    res = DiscoveryEngine.ingest_discovered_opportunity(db, payload, discovered_by=f"USER:{principal.user_id}")
    return res


@router.post("/opportunities/{opportunity_id}/approve")
def api_approve_opportunity(
    opportunity_id: str,
    body: ReviewDecisionRequest,
    principal: CaravanPrincipal = Depends(require_permission("opportunities:publish")),
    db: Session = Depends(get_db),
):
    """Approve and publish a pending funding opportunity."""
    res = DiscoveryEngine.approve_opportunity(
        db,
        opportunity_id=opportunity_id,
        reviewer_id=principal.user_id,
        reviewer_role=principal.role,
        notes=body.notes or "Approved via Admin Console",
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res.get("error"))
    return res


@router.post("/opportunities/{opportunity_id}/reject")
def api_reject_opportunity(
    opportunity_id: str,
    body: ReviewDecisionRequest,
    principal: CaravanPrincipal = Depends(require_permission("opportunities:review")),
    db: Session = Depends(get_db),
):
    """Reject and archive a candidate opportunity."""
    res = DiscoveryEngine.reject_opportunity(
        db,
        opportunity_id=opportunity_id,
        reviewer_id=principal.user_id,
        reviewer_role=principal.role,
        reason=body.reason or "Does not meet verification or institutional criteria.",
    )
    if not res.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res.get("error"))
    return res


@router.post("/opportunities/recheck-deadlines")
def api_recheck_deadlines(
    principal: CaravanPrincipal = Depends(require_permission("admin:write")),
    db: Session = Depends(get_db),
):
    """Audit and expire opportunities that have passed their deadline."""
    res = DiscoveryEngine.audit_and_recheck_deadlines(db)
    return res


@router.post("/opportunities/{opportunity_id}/detect-changes")
def api_admin_detect_changes(
    opportunity_id: str,
    incoming_data: Dict[str, Any],
    principal: CaravanPrincipal = Depends(require_permission("opportunities:review")),
    db: Session = Depends(get_db),
):
    """Detect changes in opportunity terms and stage for review."""
    return DiscoveryEngine.detect_changes_and_stage_review(
        db,
        opportunity_id=opportunity_id,
        incoming_data=incoming_data,
        actor=f"USER:{principal.user_id}",
    )


@router.post("/opportunities/verify-links")
def api_admin_verify_links(
    body: Optional[Dict[str, Any]] = None,
    principal: CaravanPrincipal = Depends(require_permission("admin:write")),
    db: Session = Depends(get_db),
):
    """Audit opportunity URLs and flag unreachable or invalid links."""
    unreachable = body.get("unreachable_urls", []) if body else []
    return DiscoveryEngine.audit_and_verify_links(
        db,
        unreachable_urls=unreachable,
        actor=f"USER:{principal.user_id}",
    )



@router.patch("/users/{user_id}/role")
def api_update_user_role(
    user_id: str,
    body: UpdateUserRoleRequest,
    principal: CaravanPrincipal = Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
):
    """Update a user's role, strictly guarded by roles:manage permission."""
    valid_roles = {
        "CUSTOMER",
        "ORGANIZATION_ADMIN",
        "SUPPORT",
        "OPPORTUNITY_REVIEWER",
        "PLATFORM_ADMIN",
        "SUPER_ADMIN",
    }
    if body.role.upper() not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(valid_roles))}",
        )

    target_user = db.get(UserRecord, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    old_role = target_user.role
    target_user.role = body.role.upper()

    audit = AuditLogRecord(
        actor=principal.user_id,
        action="USER_ROLE_CHANGED",
        resource=f"user:{user_id}",
        outcome="SUCCESS",
        details={"previous_role": old_role, "new_role": target_user.role},
    )
    db.add(audit)
    db.commit()
    db.refresh(target_user)

    return {
        "success": True,
        "user_id": target_user.user_id,
        "email": target_user.email,
        "role": target_user.role,
    }


@router.get("/audit-logs")
def api_get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    principal: CaravanPrincipal = Depends(require_permission("admin:read")),
    db: Session = Depends(get_db),
):
    """Retrieve platform operational audit logs."""
    logs = (
        db.query(AuditLogRecord)
        .order_by(AuditLogRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        {
            "log_id": l.log_id,
            "actor": l.actor,
            "action": l.action,
            "resource": l.resource,
            "outcome": l.outcome,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]

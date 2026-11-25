"""CARAVAN Standalone Platform — Admin Operations & RBAC-Protected Telemetry."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, require_permission
from app.db.models import (
    UserRecord,
    OrganizationRecord,
    FundingOpportunityRecord,
    ApplicationRecord,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Operations"])


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
        .filter(FundingOpportunityRecord.verification_status == "VERIFIED")
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
        "applications": recent_apps,
        "users": users_list,
    }

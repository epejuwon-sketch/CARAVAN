"""CARAVAN Standalone Platform — Account & Organization Profile Routes."""

from __future__ import annotations

from typing import Optional
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
    }

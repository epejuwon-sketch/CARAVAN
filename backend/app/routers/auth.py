"""CARAVAN Standalone Platform — Authentication Routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, get_current_principal
from app.services.auth_service import register_customer, authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    organization_name: str = Field(min_length=2, max_length=200)
    entity_type: str = Field(default="STARTUP", max_length=64)
    country: str = Field(default="Nigeria", max_length=80)
    state_location: str = Field(default="Abuja (FCT)", max_length=120)
    sector: str = Field(default="Technology", max_length=120)
    stage: str = Field(default="SEED", max_length=64)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def api_register(body: RegisterRequest, db: Session = Depends(get_db)):
    return register_customer(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        org_name=body.organization_name,
        entity_type=body.entity_type,
        country=body.country,
        state_location=body.state_location,
        sector=body.sector,
        stage=body.stage,
    )


@router.post("/login")
def api_login(body: LoginRequest, db: Session = Depends(get_db)):
    return authenticate_user(db, email=body.email, password=body.password)


@router.get("/me")
def api_me(principal: CaravanPrincipal = Depends(get_current_principal), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.db.models import OrganizationRecord

    org = db.execute(
        select(OrganizationRecord).where(OrganizationRecord.org_id == principal.organization_id)
    ).scalar_one_or_none()

    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "role": principal.role,
        "organization_id": principal.organization_id,
        "organization": {
            "org_id": org.org_id if org else principal.organization_id,
            "name": org.name if org else "Personal Workspace",
            "country": org.country if org else "Nigeria",
            "state_location": org.state_location if org else "Abuja (FCT)",
            "sector": org.sector if org else "Technology",
            "stage": org.stage if org else "SEED",
            "annual_revenue_ngn": getattr(org, "annual_revenue_ngn", 0.0),
            "cac_registered": getattr(org, "cac_registered", True),
            "years_in_operation": getattr(org, "years_in_operation", 1),
            "female_led": getattr(org, "female_led", False),
            "youth_led": getattr(org, "youth_led", True),
        } if org else None,
    }

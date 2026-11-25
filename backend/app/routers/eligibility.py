"""CARAVAN Standalone Platform — Eligibility Matching Routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, get_current_principal
from app.services.eligibility_service import evaluate_eligibility, get_recommendations_for_org

router = APIRouter(prefix="/api/v1/eligibility", tags=["Eligibility & Matching"])


from pydantic import BaseModel
from typing import Optional


class AssessRequestBody(BaseModel):
    opportunity_id: str


@router.post("/assess/{opportunity_id}")
def api_assess_opportunity_path(
    opportunity_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return evaluate_eligibility(
        db,
        org_id=principal.organization_id,
        opportunity_id=opportunity_id,
    )


@router.post("/assess")
def api_assess_opportunity_body(
    body: AssessRequestBody,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return evaluate_eligibility(
        db,
        org_id=principal.organization_id,
        opportunity_id=body.opportunity_id,
    )


@router.get("/recommendations")
def api_get_recommendations(
    limit: int = Query(default=20, ge=1, le=50),
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    recommendations = get_recommendations_for_org(
        db,
        org_id=principal.organization_id,
        limit=limit,
    )
    return {"total": len(recommendations), "recommendations": recommendations}

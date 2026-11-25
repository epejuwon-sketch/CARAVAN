"""CARAVAN Standalone Platform — Saved Opportunities Bookmark Routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import SavedOpportunityRecord, FundingOpportunityRecord, gen_id
from app.core.permissions import CaravanPrincipal, get_current_principal

router = APIRouter(prefix="/api/v1/saved", tags=["Saved Opportunities"])


class SaveOpportunityRequest(BaseModel):
    opportunity_id: str
    notes: str = ""


@router.get("")
def api_list_saved(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    saved = db.execute(
        select(SavedOpportunityRecord).where(SavedOpportunityRecord.organization_id == principal.organization_id)
    ).scalars().all()

    items = []
    for s in saved:
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == s.opportunity_id)
        ).scalar_one_or_none()
        items.append({
            "saved_id": s.saved_id,
            "opportunity_id": s.opportunity_id,
            "title": opp.title if opp else "Unknown",
            "provider": opp.provider if opp else "Unknown",
            "funding_type": opp.funding_type if opp else "GRANT",
            "amount_display": opp.amount_display if opp else "Undisclosed",
            "deadline_at": opp.deadline_at.isoformat() if opp and opp.deadline_at else None,
            "notes": s.notes,
            "saved_at": s.saved_at.isoformat(),
        })
    return {"total": len(items), "saved": items}


@router.post("", status_code=status.HTTP_201_CREATED)
def api_save_opportunity(
    body: SaveOpportunityRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    existing = db.execute(
        select(SavedOpportunityRecord).where(
            SavedOpportunityRecord.organization_id == principal.organization_id,
            SavedOpportunityRecord.opportunity_id == body.opportunity_id,
        )
    ).scalar_one_or_none()
    if existing:
        return {"saved_id": existing.saved_id, "saved": True, "already_saved": True}

    rec = SavedOpportunityRecord(
        saved_id=gen_id("sav"),
        organization_id=principal.organization_id,
        opportunity_id=body.opportunity_id,
        notes=body.notes or "",
    )
    db.add(rec)
    db.commit()
    return {"saved_id": rec.saved_id, "opportunity_id": rec.opportunity_id, "saved": True}


@router.post("/{opportunity_id}", status_code=status.HTTP_200_OK)
def api_save_opportunity_path(
    opportunity_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    existing = db.execute(
        select(SavedOpportunityRecord).where(
            SavedOpportunityRecord.organization_id == principal.organization_id,
            SavedOpportunityRecord.opportunity_id == opportunity_id,
        )
    ).scalar_one_or_none()
    if existing:
        return {"saved_id": existing.saved_id, "saved": True, "already_saved": True}

    rec = SavedOpportunityRecord(
        saved_id=gen_id("sav"),
        organization_id=principal.organization_id,
        opportunity_id=opportunity_id,
        notes="",
    )
    db.add(rec)
    db.commit()
    return {"saved_id": rec.saved_id, "opportunity_id": rec.opportunity_id, "saved": True}


@router.delete("/{saved_id}")
def api_delete_saved(
    saved_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    rec = db.execute(
        select(SavedOpportunityRecord).where(
            SavedOpportunityRecord.saved_id == saved_id,
            SavedOpportunityRecord.organization_id == principal.organization_id,
        )
    ).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found.")
    db.delete(rec)
    db.commit()
    return {"status": "DELETED", "saved_id": saved_id}

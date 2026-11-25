"""CARAVAN Standalone Platform — Funding Opportunities Marketplace Routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.opportunity_service import list_opportunities, get_opportunity_detail, FUNDING_CATEGORIES

router = APIRouter(prefix="/api/v1/opportunities", tags=["Opportunities"])


@router.get("")
def api_list_opportunities(
    query: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    geo: Optional[str] = Query(default=None),
    sector: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    open_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_opportunities(
        db,
        query=query,
        category=category,
        geo=geo,
        sector=sector,
        status_filter=status,
        open_only=open_only,
        limit=limit,
        offset=offset,
    )


@router.get("/categories")
def api_list_categories():
    return {"categories": FUNDING_CATEGORIES}


@router.get("/{opportunity_id}")
def api_opportunity_detail(opportunity_id: str, db: Session = Depends(get_db)):
    return get_opportunity_detail(db, opportunity_id=opportunity_id)

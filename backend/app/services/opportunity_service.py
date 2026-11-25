"""CARAVAN Standalone Platform — Funding Intelligence & Marketplace Service."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models import FundingOpportunityRecord, SavedOpportunityRecord, AuditLogRecord, gen_id

FUNDING_CATEGORIES = [
    {"id": "GRANT", "label": "Non-Dilutive Grants", "description": "Direct institutional grants with no equity required"},
    {"id": "LOAN", "label": "Concessionary Debt & Loans", "description": "Low-interest commercial or public development loans"},
    {"id": "VENTURE_CAPITAL", "label": "Venture Capital", "description": "Institutional Series A, B, and Growth venture funds"},
    {"id": "ANGEL_INVESTMENT", "label": "Angel Investment", "description": "High-net-worth accredited angel syndicate networks"},
    {"id": "SEED_FUNDING", "label": "Pre-Seed & Seed Equity", "description": "Early stage institutional startup equity financing"},
    {"id": "ACCELERATOR", "label": "Accelerators & Incubators", "description": "Cohort-based capital, mentorship, and commercial scale"},
    {"id": "COMPETITION", "label": "Competitions & Challenges", "description": "Innovation prize challenges and business plan contests"},
    {"id": "AWARD", "label": "Merit Honors & Awards", "description": "Civic, scientific, and industry recognition prizes"},
    {"id": "WORKING_CAPITAL", "label": "Working Capital Facilities", "description": "Invoice factoring, trade credit, and cash flow facilities"},
    {"id": "EQUIPMENT_FINANCING", "label": "Equipment & Asset Financing", "description": "Leasing and capex debt for industrial and tech machinery"},
    {"id": "CORPORATE_FUNDING", "label": "Corporate Venture & Innovation", "description": "Corporate strategic venture funds and pilot grants"},
    {"id": "INSTITUTIONAL_FINANCE", "label": "Development & DFI Finance", "description": "Multilateral, AfDB, IFC, and sovereign funding programs"},
    {"id": "RESEARCH_FUNDING", "label": "R&D & Science Grants", "description": "Academic and industrial technological research grants"},
    {"id": "PHILANTHROPIC_FUNDING", "label": "Philanthropic Foundations", "description": "Impact, health, climate, and social venture programs"},
    {"id": "SCHOLARSHIP", "label": "Executive Fellowships & Scholarships", "description": "Leadership, tech talent, and research training fellowships"},
]


def list_opportunities(
    db: Session,
    query: Optional[str] = None,
    category: Optional[str] = None,
    geo: Optional[str] = None,
    sector: Optional[str] = None,
    status_filter: Optional[str] = None,
    open_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    stmt = select(FundingOpportunityRecord)
    filters = []

    if query:
        q_clean = f"%{query.strip().lower()}%"
        filters.append(
            or_(
                FundingOpportunityRecord.title.ilike(q_clean),
                FundingOpportunityRecord.provider.ilike(q_clean),
                FundingOpportunityRecord.applicant_eligibility.ilike(q_clean),
            )
        )
    if category:
        filters.append(FundingOpportunityRecord.funding_type == category.upper())
    if geo:
        filters.append(FundingOpportunityRecord.geographic_eligibility.ilike(f"%{geo.strip()}%"))
    if sector:
        filters.append(FundingOpportunityRecord.industry_sector.ilike(f"%{sector.strip()}%"))
    if status_filter:
        filters.append(FundingOpportunityRecord.verification_status == status_filter.upper())
    if open_only:
        now = datetime.now(timezone.utc)
        filters.append(
            or_(
                FundingOpportunityRecord.is_rolling.is_(True),
                FundingOpportunityRecord.deadline_at.is_(None),
                FundingOpportunityRecord.deadline_at >= now,
            )
        )

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(desc(FundingOpportunityRecord.verified_at)).limit(limit).offset(offset)
    records = db.execute(stmt).scalars().all()

    # Count total
    total = len(records)

    return {
        "total": total,
        "categories": FUNDING_CATEGORIES,
        "opportunities": [
            {
                "opportunity_id": r.opportunity_id,
                "title": r.title,
                "provider": r.provider,
                "funding_type": r.funding_type,
                "amount_min": r.amount_min,
                "amount_max": r.amount_max,
                "currency": r.currency,
                "amount_display": r.amount_display,
                "geographic_eligibility": r.geographic_eligibility,
                "applicant_eligibility": r.applicant_eligibility,
                "industry_sector": r.industry_sector,
                "application_requirements": r.application_requirements,
                "opening_date": r.opening_date.isoformat() if r.opening_date else None,
                "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
                "is_rolling": r.is_rolling,
                "official_source_url": r.official_source_url,
                "verification_status": r.verification_status,
                "verified_at": r.verified_at.isoformat() if r.verified_at else None,
                "source_name": r.source_name,
            }
            for r in records
        ],
    }


def get_opportunity_detail(db: Session, opportunity_id: str) -> dict:
    r = db.execute(
        select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Funding opportunity '{opportunity_id}' not found.",
        )
    return {
        "opportunity_id": r.opportunity_id,
        "title": r.title,
        "provider": r.provider,
        "funding_type": r.funding_type,
        "amount_min": r.amount_min,
        "amount_max": r.amount_max,
        "currency": r.currency,
        "amount_display": r.amount_display,
        "geographic_eligibility": r.geographic_eligibility,
        "applicant_eligibility": r.applicant_eligibility,
        "industry_sector": r.industry_sector,
        "application_requirements": r.application_requirements,
        "opening_date": r.opening_date.isoformat() if r.opening_date else None,
        "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
        "is_rolling": r.is_rolling,
        "official_source_url": r.official_source_url,
        "verification_status": r.verification_status,
        "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        "source_name": r.source_name,
        "provenance_hash": r.provenance_hash,
    }


def create_verified_opportunity(
    db: Session,
    title: str,
    provider: str,
    funding_type: str,
    amount_min: Optional[float],
    amount_max: Optional[float],
    currency: str,
    amount_display: str,
    geographic_eligibility: str,
    applicant_eligibility: str,
    industry_sector: str,
    application_requirements: List[str],
    official_source_url: str,
    deadline_at: Optional[datetime] = None,
    is_rolling: bool = False,
    source_name: str = "Institutional Verification Portal",
    actor: str = "admin",
) -> FundingOpportunityRecord:
    prov_str = f"{title}:{provider}:{official_source_url}"
    prov_hash = hashlib.sha256(prov_str.encode("utf-8")).hexdigest()

    opp = FundingOpportunityRecord(
        opportunity_id=gen_id("opp"),
        title=title.strip(),
        provider=provider.strip(),
        funding_type=funding_type.upper(),
        amount_min=amount_min,
        amount_max=amount_max,
        currency=currency,
        amount_display=amount_display,
        geographic_eligibility=geographic_eligibility,
        applicant_eligibility=applicant_eligibility,
        industry_sector=industry_sector,
        application_requirements=application_requirements,
        official_source_url=official_source_url,
        deadline_at=deadline_at,
        is_rolling=is_rolling,
        verification_status="VERIFIED",
        source_name=source_name,
        provenance_hash=prov_hash,
    )
    db.add(opp)
    audit = AuditLogRecord(
        actor=actor,
        action="OPPORTUNITY_CREATED",
        resource=f"opportunity:{opp.opportunity_id}",
        details={"title": title, "provider": provider, "funding_type": funding_type},
    )
    db.add(audit)
    db.commit()
    db.refresh(opp)
    return opp

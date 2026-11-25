"""CARAVAN Standalone Platform — Funding Intelligence & Marketplace Service."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, or_, desc, func
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


def make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_live_status(r: FundingOpportunityRecord, now: Optional[datetime] = None) -> str:
    """Accurately compute live operational status without human lag."""
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    explicit_status = (getattr(r, "opportunity_status", None) or getattr(r, "verification_status", "OPEN")).upper()
    if explicit_status in ("CLOSED", "SUSPENDED", "PAUSED", "REJECTED"):
        return explicit_status
    if getattr(r, "is_rolling", False):
        return "ROLLING"
    
    opening_date = make_aware(r.opening_date)
    if opening_date and opening_date > now:
        return "UPCOMING"
    
    deadline_at = make_aware(r.deadline_at)
    if deadline_at:
        if now > deadline_at:
            return "CLOSED"
        if (deadline_at - now).total_seconds() <= 7 * 86400:
            return "CLOSING_SOON"
    return "OPEN"


def serialize_opportunity(r: FundingOpportunityRecord, detail: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    live_status = compute_live_status(r, now)
    
    data = {
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
        "application_requirements": r.application_requirements or [],
        "opening_date": r.opening_date.isoformat() if r.opening_date else None,
        "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
        "is_rolling": r.is_rolling,
        "official_source_url": r.official_source_url,
        "official_application_url": getattr(r, "official_application_url", None) or r.official_source_url,
        "supporting_source_urls": getattr(r, "supporting_source_urls", []) or [],
        "eligible_applicant_types": getattr(r, "eligible_applicant_types", []) or [],
        "eligible_countries": getattr(r, "eligible_countries", []) or [],
        "eligible_states": getattr(r, "eligible_states", []) or [],
        "eligible_sectors": getattr(r, "eligible_sectors", []) or [],
        "funding_structure": getattr(r, "funding_structure", "DIRECT_DISBURSEMENT"),
        "business_stage": getattr(r, "business_stage", "ALL_STAGES"),
        "age_restrictions": getattr(r, "age_restrictions", "NO_RESTRICTION"),
        "registration_required": getattr(r, "registration_required", True),
        "application_method": getattr(r, "application_method", "ONLINE_PORTAL"),
        "opportunity_status": live_status,
        "important_conditions": getattr(r, "important_conditions", ""),
        "verification_status": r.verification_status,
        "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        "source_name": r.source_name,
        "confidence_score": getattr(r, "confidence_score", 1.0),
        "evidence_completeness": getattr(r, "evidence_completeness", "COMPLETE"),
        "publication_status": getattr(r, "publication_status", "PUBLISHED"),
    }
    if detail:
        data.update({
            "provenance_hash": r.provenance_hash,
            "source_retrieval_at": r.source_retrieval_at.isoformat() if getattr(r, "source_retrieval_at", None) else None,
            "verification_method": getattr(r, "verification_method", "MANUAL_REGISTRY_AUDIT"),
            "verification_evidence": getattr(r, "verification_evidence", {}),
            "last_checked_at": r.last_checked_at.isoformat() if getattr(r, "last_checked_at", None) else None,
            "next_verification_at": r.next_verification_at.isoformat() if getattr(r, "next_verification_at", None) else None,
            "verification_history": getattr(r, "verification_history", []),
        })
    return data


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
        s_upper = status_filter.upper()
        filters.append(
            or_(
                FundingOpportunityRecord.verification_status == s_upper,
                FundingOpportunityRecord.opportunity_status == s_upper,
            )
        )
    if open_only:
        now = datetime.now(timezone.utc)
        filters.append(
            and_(
                FundingOpportunityRecord.opportunity_status != "CLOSED",
                or_(
                    FundingOpportunityRecord.is_rolling.is_(True),
                    FundingOpportunityRecord.deadline_at.is_(None),
                    FundingOpportunityRecord.deadline_at >= now,
                ),
            )
        )

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(desc(FundingOpportunityRecord.verified_at)).limit(limit).offset(offset)
    records = db.execute(stmt).scalars().all()

    # Count total matching opportunities in database (independent of pagination limit)
    count_stmt = select(func.count(FundingOpportunityRecord.opportunity_id))
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    total = db.execute(count_stmt).scalar() or 0

    return {
        "total": total,
        "categories": FUNDING_CATEGORIES,
        "opportunities": [serialize_opportunity(r) for r in records],
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
    return serialize_opportunity(r, detail=True)


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

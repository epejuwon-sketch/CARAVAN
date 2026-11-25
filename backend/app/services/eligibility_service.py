"""CARAVAN Standalone Platform — Eligibility Matching & Recommendations Engine."""

from __future__ import annotations

from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models import (
    OrganizationRecord,
    FundingOpportunityRecord,
    EligibilityAssessmentRecord,
    AuditLogRecord,
    gen_id,
)


def evaluate_eligibility(db: Session, org_id: str, opportunity_id: str) -> dict:
    org = db.execute(select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization profile not found.")

    opp = db.execute(select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funding opportunity not found.")

    score = 40.0  # Base score for valid active venture
    breakdown = {}

    # 1. Geographic match (weight: 25)
    opp_geo = opp.geographic_eligibility.lower()
    org_country = org.country.lower()
    if org_country in opp_geo or "global" in opp_geo or "africa" in opp_geo:
        score += 25.0
        breakdown["geography"] = {"matched": True, "score": 25, "reason": f"Matches geographic scope '{opp.geographic_eligibility}'"}
    else:
        breakdown["geography"] = {"matched": False, "score": 0, "reason": f"Requires '{opp.geographic_eligibility}'"}

    # 2. Sector match (weight: 20)
    opp_sector = opp.industry_sector.lower()
    org_sector = org.sector.lower()
    if opp_sector in ("multi-sector", "all", "general") or org_sector in opp_sector:
        score += 20.0
        breakdown["sector"] = {"matched": True, "score": 20, "reason": f"Matches industry sector '{opp.industry_sector}'"}
    else:
        score += 5.0
        breakdown["sector"] = {"matched": "partial", "score": 5, "reason": f"Cross-disciplinary applicability for '{opp.industry_sector}'"}

    # 3. Stage & Entity Type match (weight: 15)
    opp_elig = opp.applicant_eligibility.lower()
    org_stage = org.stage.lower()
    org_type = org.entity_type.lower()
    if org_stage in opp_elig or org_type in opp_elig or "startup" in opp_elig or "sme" in opp_elig:
        score += 15.0
        breakdown["stage_and_entity"] = {"matched": True, "score": 15, "reason": f"Stage '{org.stage}' and entity '{org.entity_type}' eligible."}
    else:
        score += 5.0
        breakdown["stage_and_entity"] = {"matched": "partial", "score": 5, "reason": "Eligible subject to co-founder or registration criteria."}

    # Cap score at 100
    final_score = min(100.0, score)

    if final_score >= 80.0:
        recommendation = "STRONG"
    elif final_score >= 60.0:
        recommendation = "MODERATE"
    elif final_score >= 40.0:
        recommendation = "WEAK"
    else:
        recommendation = "INELIGIBLE"

    # Persist or update assessment
    existing = db.execute(
        select(EligibilityAssessmentRecord).where(
            EligibilityAssessmentRecord.organization_id == org_id,
            EligibilityAssessmentRecord.opportunity_id == opportunity_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.match_score = final_score
        existing.recommendation_level = recommendation
        existing.criteria_breakdown = breakdown
        assessment_id = existing.assessment_id
    else:
        assessment_id = gen_id("ass")
        assessment = EligibilityAssessmentRecord(
            assessment_id=assessment_id,
            organization_id=org_id,
            opportunity_id=opportunity_id,
            match_score=final_score,
            recommendation_level=recommendation,
            criteria_breakdown=breakdown,
        )
        db.add(assessment)

    db.commit()

    return {
        "assessment_id": assessment_id,
        "organization_id": org_id,
        "opportunity_id": opportunity_id,
        "opportunity_title": opp.title,
        "provider": opp.provider,
        "match_score": final_score,
        "recommendation_level": recommendation,
        "criteria_breakdown": breakdown,
    }


def get_recommendations_for_org(db: Session, org_id: str, limit: int = 20) -> List[dict]:
    # Run matching for top open opportunities
    opportunities = db.execute(
        select(FundingOpportunityRecord).where(
            FundingOpportunityRecord.verification_status.in_(["VERIFIED", "VERIFIED_OPEN", "UPCOMING_CONFIRMED", "UPCOMING"])
        ).limit(limit)
    ).scalars().all()

    results = []
    for opp in opportunities:
        res = evaluate_eligibility(db, org_id, opp.opportunity_id)
        results.append(res)

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results

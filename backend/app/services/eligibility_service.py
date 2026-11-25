"""CARAVAN Standalone Platform — Transparent Eligibility Matching & Intelligence Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models import (
    OrganizationRecord,
    FundingOpportunityRecord,
    EligibilityAssessmentRecord,
    gen_id,
)
from app.services.opportunity_service import compute_live_status


def evaluate_eligibility(db: Session, org_id: str, opportunity_id: str) -> dict:
    """Evaluate an organization's eligibility against an opportunity with zero AI hallucinations."""
    org = db.execute(select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization profile not found.")

    opp = db.execute(select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funding opportunity not found.")

    now = datetime.now(timezone.utc)
    live_status = compute_live_status(opp, now)

    score = 0.0
    breakdown: Dict[str, Any] = {}
    missing_requirements: List[str] = []
    strengths: List[str] = []
    disqualifications: List[str] = []
    is_disqualified = False

    # 1. Operational & Lifecycle Status Check
    if live_status == "CLOSED":
        is_disqualified = True
        disqualifications.append(f"Opportunity is CLOSED. Application window concluded on {opp.deadline_at.strftime('%d %b %Y') if opp.deadline_at else 'previous cohort'}.")
        breakdown["operational_status"] = {
            "matched": False,
            "score": 0,
            "status": "CLOSED",
            "reason": "Applications are closed for this cycle.",
        }
    else:
        breakdown["operational_status"] = {
            "matched": True,
            "score": 10,
            "status": live_status,
            "reason": f"Opportunity is actively open ({live_status}).",
        }
        score += 10.0

    # 2. Geographic Scope (weight: 25)
    opp_geo = (opp.geographic_eligibility or "").lower()
    org_country = (org.country or "Nigeria").lower()
    org_state = (org.state_location or "").lower()
    geo_matched = False

    if org_country in opp_geo or "global" in opp_geo or "africa" in opp_geo or "pan-african" in opp_geo:
        # Check state-level restrictions if applicable
        if opp.eligible_states and opp.eligible_states != ["All States"] and opp.eligible_states != ["All"]:
            matching_states = [s.lower() for s in opp.eligible_states]
            if any(s in org_state for s in matching_states):
                score += 25.0
                geo_matched = True
                strengths.append(f"Matches state jurisdiction ({org.state_location}).")
                breakdown["geography"] = {"matched": True, "score": 25, "reason": f"Enterprise located in eligible territory: {org.state_location}, {org.country}."}
            else:
                is_disqualified = True
                disqualifications.append(f"Restricted to {', '.join(opp.eligible_states)}. Applicant is in {org.state_location}.")
                breakdown["geography"] = {"matched": False, "score": 0, "reason": f"Restricted to: {', '.join(opp.eligible_states)}."}
        else:
            score += 25.0
            geo_matched = True
            strengths.append(f"Matches geographic territory ({opp.geographic_eligibility}).")
            breakdown["geography"] = {"matched": True, "score": 25, "reason": f"Enterprise located in eligible scope: {opp.geographic_eligibility}."}
    else:
        is_disqualified = True
        disqualifications.append(f"Country {org.country} is outside eligible scope ({opp.geographic_eligibility}).")
        breakdown["geography"] = {"matched": False, "score": 0, "reason": f"Restricted to: {opp.geographic_eligibility}."}

    # 3. Industry Sector Scope (weight: 20)
    opp_sector = (opp.industry_sector or "").lower()
    org_sector = (org.sector or "").lower()
    if any(k in opp_sector for k in ["multi-sector", "all", "general", "across all sectors"]) or org_sector in opp_sector:
        score += 20.0
        strengths.append(f"Direct sector alignment: {org.sector}.")
        breakdown["sector"] = {"matched": True, "score": 20, "reason": f"Direct sector alignment with '{opp.industry_sector}'."}
    else:
        score += 8.0
        breakdown["sector"] = {"matched": "partial", "score": 8, "reason": f"Secondary cross-sector alignment with '{opp.industry_sector}'."}

    # 4. Entity Type & Operating Stage (weight: 15)
    opp_elig_text = (opp.applicant_eligibility or "").lower()
    org_type = (org.entity_type or "STARTUP").upper()
    eligible_types = [t.upper() for t in (opp.eligible_applicant_types or [])]

    if not eligible_types or org_type in eligible_types or org_type.lower() in opp_elig_text:
        score += 15.0
        strengths.append(f"Entity structure '{org.entity_type}' is fully recognized.")
        breakdown["entity_type"] = {"matched": True, "score": 15, "reason": f"Entity type '{org.entity_type}' is eligible."}
    else:
        score += 5.0
        missing_requirements.append(f"Targeted primarily at {', '.join(eligible_types)}.")
        breakdown["entity_type"] = {"matched": "partial", "score": 5, "reason": f"Targeted at: {', '.join(eligible_types)}."}

    # 5. CAC / Corporate Registration Requirement (weight: 15)
    reg_required = getattr(opp, "registration_required", True)
    cac_registered = getattr(org, "cac_registered", True)

    if reg_required:
        if cac_registered:
            score += 15.0
            strengths.append("Verified CAC Corporate Registration.")
            breakdown["registration"] = {"matched": True, "score": 15, "reason": "Corporate registration requirements met."}
        else:
            missing_requirements.append("Formal CAC Business Registration is required.")
            breakdown["registration"] = {"matched": False, "score": 0, "reason": "Requires active CAC incorporation / business name."}
    else:
        score += 15.0
        breakdown["registration"] = {"matched": True, "score": 15, "reason": "No mandatory pre-registration requirement."}

    # 6. Gender-Lens / Women-Led Criteria
    title_lower = opp.title.lower()
    requires_female_led = any(kw in title_lower or kw in opp_elig_text for kw in ["for women", "women-led", "female-led", "female entrepreneur", "female founders", "w-initiative", "grow accelerator"])
    org_female_led = getattr(org, "female_led", False)

    if requires_female_led:
        if org_female_led:
            score += 15.0
            strengths.append("Qualified for Gender-Lens / Female-Led funding window.")
            breakdown["female_led"] = {"matched": True, "score": 15, "reason": "Confirmed female-led enterprise leadership."}
        else:
            is_disqualified = True
            disqualifications.append("Exclusive to female-led or women-owned enterprises (51%+ female equity).")
            breakdown["female_led"] = {"matched": False, "score": 0, "reason": "Exclusive to women-led enterprises."}
    else:
        breakdown["female_led"] = {"matched": True, "score": 0, "reason": "Open to all founders regardless of gender."}

    # 7. Revenue Thresholds (e.g. GROW Accelerator requires ₦20m turnover)
    if "grow accelerator" in title_lower:
        org_rev_ngn = getattr(org, "annual_revenue_ngn", 0.0)
        org_rev_usd = getattr(org, "annual_revenue_usd", 0.0)
        effective_rev = max(org_rev_ngn, org_rev_usd * 1500)
        if effective_rev >= 20000000:
            strengths.append(f"Turnover threshold exceeded (₦{effective_rev:,.0f} >= ₦20m).")
            breakdown["revenue"] = {"matched": True, "score": 0, "reason": f"Meets ₦20,000,000 revenue qualification (reported ₦{effective_rev:,.0f})."}
        else:
            is_disqualified = True
            disqualifications.append(f"Requires verified minimum annual turnover of ₦20,000,000. Current reported: ₦{effective_rev:,.0f}.")
            breakdown["revenue"] = {"matched": False, "score": 0, "reason": "Requires minimum ₦20m annual turnover."}

    # Cap score at 100
    final_score = min(100.0, max(0.0, score))

    if is_disqualified:
        recommendation = "INELIGIBLE"
        final_score = min(final_score, 35.0)
    elif final_score >= 80.0:
        recommendation = "STRONG"
    elif final_score >= 50.0:
        recommendation = "MODERATE"
    else:
        recommendation = "WEAK"

    # Persist or update assessment
    existing = db.execute(
        select(EligibilityAssessmentRecord).where(
            EligibilityAssessmentRecord.organization_id == org_id,
            EligibilityAssessmentRecord.opportunity_id == opportunity_id,
        )
    ).scalar_one_or_none()

    breakdown_payload = {
        **breakdown,
        "breakdown": breakdown,
        "strengths": strengths,
        "missing_requirements": missing_requirements,
        "disqualifications": disqualifications,
        "live_status": live_status,
        "official_source_url": opp.official_source_url,
        "official_application_url": getattr(opp, "official_application_url", None) or opp.official_source_url,
        "important_conditions": getattr(opp, "important_conditions", ""),
    }

    if existing:
        existing.match_score = final_score
        existing.recommendation_level = recommendation
        existing.criteria_breakdown = breakdown_payload
        assessment_id = existing.assessment_id
    else:
        assessment_id = gen_id("ass")
        assessment = EligibilityAssessmentRecord(
            assessment_id=assessment_id,
            organization_id=org_id,
            opportunity_id=opportunity_id,
            match_score=final_score,
            recommendation_level=recommendation,
            criteria_breakdown=breakdown_payload,
        )
        db.add(assessment)

    db.commit()

    return {
        "assessment_id": assessment_id,
        "organization_id": org_id,
        "opportunity_id": opportunity_id,
        "opportunity_title": opp.title,
        "provider": opp.provider,
        "funding_type": opp.funding_type,
        "amount_display": opp.amount_display,
        "match_score": final_score,
        "recommendation_level": recommendation,
        "criteria_breakdown": breakdown_payload,
        "is_disqualified": is_disqualified,
        "disqualifications": disqualifications,
        "strengths": strengths,
        "missing_requirements": missing_requirements,
        "live_status": live_status,
        "official_source_url": opp.official_source_url,
        "official_application_url": getattr(opp, "official_application_url", None) or opp.official_source_url,
    }


def get_recommendations_for_org(db: Session, org_id: str, limit: int = 50) -> Dict[str, Any]:
    """Retrieve categorized recommendations with full transparency."""
    opportunities = db.execute(
        select(FundingOpportunityRecord).order_by(FundingOpportunityRecord.title.asc())
    ).scalars().all()

    all_results = []
    strong_matches = []
    possible_matches = []
    ineligible_opportunities = []

    for opp in opportunities:
        res = evaluate_eligibility(db, org_id, opp.opportunity_id)
        all_results.append(res)
        if res["recommendation_level"] == "STRONG":
            strong_matches.append(res)
        elif res["recommendation_level"] == "MODERATE":
            possible_matches.append(res)
        else:
            ineligible_opportunities.append(res)

    all_results.sort(key=lambda x: x["match_score"], reverse=True)
    strong_matches.sort(key=lambda x: x["match_score"], reverse=True)
    possible_matches.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "recommendations": all_results[:limit],
        "strong_matches": strong_matches,
        "possible_matches": possible_matches,
        "ineligible_opportunities": ineligible_opportunities,
        "total_evaluated": len(all_results),
        "total_strong": len(strong_matches),
        "total_possible": len(possible_matches),
        "total_ineligible": len(ineligible_opportunities),
    }

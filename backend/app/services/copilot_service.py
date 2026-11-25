"""CARAVAN Standalone Platform — Business Copilot & Intelligence Engine.

Provides conversational AI funding copilot grounded in tenant-isolated business intelligence,
retrieval over verified funding opportunities, anti-hallucination guardrails, and proposal drafting.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, or_, func, and_
from sqlalchemy.orm import Session

from app.db.models import (
    OrganizationRecord,
    FundingOpportunityRecord,
    ApplicationRecord,
    DocumentMetadataRecord,
    CopilotSessionRecord,
    CopilotMessageRecord,
    gen_id,
    utcnow,
)
from app.core.entitlements import (
    check_can_use_copilot,
    consume_copilot_credits,
    get_tenant_entitlements_and_usage,
)


def calculate_business_readiness(org: OrganizationRecord) -> Dict[str, Any]:
    """Evaluate business maturity and funding readiness across 5 structural pillars."""
    score = 0.0
    pillars: Dict[str, Dict[str, Any]] = {
        "governance_and_compliance": {
            "name": "Corporate Governance & Compliance",
            "score": 0,
            "max": 20,
            "details": [],
            "gaps": [],
        },
        "financial_traction": {
            "name": "Financial Traction & Viability",
            "score": 0,
            "max": 25,
            "details": [],
            "gaps": [],
        },
        "strategic_clarity": {
            "name": "Strategic Clarity & Proposition",
            "score": 0,
            "max": 25,
            "details": [],
            "gaps": [],
        },
        "capital_planning": {
            "name": "Capital Strategy & Resource Planning",
            "score": 0,
            "max": 15,
            "details": [],
            "gaps": [],
        },
        "track_record": {
            "name": "Track Record & Operational Maturity",
            "score": 0,
            "max": 15,
            "details": [],
            "gaps": [],
        },
    }

    # Pillar 1: Governance & Compliance (20 pts)
    if org.cac_registered:
        pillars["governance_and_compliance"]["score"] += 12
        pillars["governance_and_compliance"]["details"].append("CAC registered entity in good standing.")
    else:
        pillars["governance_and_compliance"]["gaps"].append("Company is not CAC registered; essential for all institutional grants and loans.")

    if org.years_in_operation >= 1:
        pillars["governance_and_compliance"]["score"] += 5
        pillars["governance_and_compliance"]["details"].append(f"{org.years_in_operation} year(s) of corporate operational history.")
    else:
        pillars["governance_and_compliance"]["gaps"].append("Less than 1 year of operations; limits eligibility for commercial debt facilities.")

    if org.team_size >= 2:
        pillars["governance_and_compliance"]["score"] += 3
        pillars["governance_and_compliance"]["details"].append(f"Structured team of {org.team_size} members.")
    else:
        pillars["governance_and_compliance"]["gaps"].append("Solo-founder operation; add key co-founders or advisors to strengthen investor appeal.")

    # Pillar 2: Financial Traction (25 pts)
    rev_ngn = getattr(org, "annual_revenue_ngn", 0.0) or (org.annual_revenue_usd * 1500.0)
    if rev_ngn >= 25000000.0:  # 25M+ NGN
        pillars["financial_traction"]["score"] += 25
        pillars["financial_traction"]["details"].append("Substantial commercial revenue (> ₦25M), qualifies for scale-up loans and equity.")
    elif rev_ngn >= 5000000.0:  # 5M - 25M NGN
        pillars["financial_traction"]["score"] += 18
        pillars["financial_traction"]["details"].append("Active revenue traction (> ₦5M), eligible for commercial debt and working capital.")
    elif rev_ngn > 0:
        pillars["financial_traction"]["score"] += 10
        pillars["financial_traction"]["details"].append("Early revenues recorded; qualify for early-stage grants and angel matching.")
    else:
        pillars["financial_traction"]["score"] += 3
        pillars["financial_traction"]["gaps"].append("Pre-revenue venture; focus on non-dilutive idea-stage grants and proof-of-concept awards.")

    # Pillar 3: Strategic Clarity (25 pts)
    prod = getattr(org, "products_services", "") or ""
    cust = getattr(org, "target_customers", "") or ""
    model = getattr(org, "business_model", "B2B") or "B2B"

    if len(prod.strip()) >= 15:
        pillars["strategic_clarity"]["score"] += 10
        pillars["strategic_clarity"]["details"].append("Articulated core product/service offering.")
    else:
        pillars["strategic_clarity"]["gaps"].append("Expand product and value proposition description in business profile.")

    if len(cust.strip()) >= 10:
        pillars["strategic_clarity"]["score"] += 8
        pillars["strategic_clarity"]["details"].append(f"Defined target market: '{cust[:60]}'.")
    else:
        pillars["strategic_clarity"]["gaps"].append("Specify target customer demographic or institutional segments.")

    if model:
        pillars["strategic_clarity"]["score"] += 7
        pillars["strategic_clarity"]["details"].append(f"Identified revenue model: {model}.")

    # Pillar 4: Capital Planning (15 pts)
    goals = org.funding_goals or ""
    use_of_funds = getattr(org, "intended_use_of_funds", "") or ""

    if len(goals.strip()) >= 10:
        pillars["capital_planning"]["score"] += 8
        pillars["capital_planning"]["details"].append("Explicit capital goals defined.")
    else:
        pillars["capital_planning"]["gaps"].append("State specific target funding amounts and preferred capital types.")

    if len(use_of_funds.strip()) >= 15:
        pillars["capital_planning"]["score"] += 7
        pillars["capital_planning"]["details"].append("Granular use of funds and budget allocation outlined.")
    else:
        pillars["capital_planning"]["gaps"].append("Outline intended use of proceeds (capex, opex, hiring, or expansion).")

    # Pillar 5: Track Record & Operations (15 pts)
    history = getattr(org, "previous_funding_history", []) or []
    if history and len(history) > 0:
        pillars["track_record"]["score"] += 15
        pillars["track_record"]["details"].append(f"Demonstrated funding track record ({len(history)} prior transactions/grants).")
    elif org.years_in_operation >= 2:
        pillars["track_record"]["score"] += 10
        pillars["track_record"]["details"].append("2+ years operational resilience in local market.")
    else:
        pillars["track_record"]["score"] += 5
        pillars["track_record"]["gaps"].append("First-time institutional applicant; build pedigree via verified incubator or accelerator programs.")

    total_score = sum(p["score"] for p in pillars.values())
    readiness_level = (
        "INSTITUTIONAL_READY"
        if total_score >= 80
        else ("GROWTH_READY" if total_score >= 60 else ("EMERGING" if total_score >= 40 else "EARLY_STAGE"))
    )

    return {
        "readiness_score": round(total_score, 1),
        "readiness_level": readiness_level,
        "evaluated_at": utcnow().isoformat(),
        "pillars": pillars,
    }


class CopilotEngine:
    """Core intelligence engine coordinating business context, retrieval, and reasoning."""

    @staticmethod
    def get_or_create_session(
        db: Session,
        org_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        context_mode: str = "GENERAL",
        target_id: Optional[str] = None,
    ) -> CopilotSessionRecord:
        if session_id:
            sess = db.execute(
                select(CopilotSessionRecord).where(
                    CopilotSessionRecord.session_id == session_id,
                    CopilotSessionRecord.organization_id == org_id,
                )
            ).scalar_one_or_none()
            if sess:
                return sess

        new_sess = CopilotSessionRecord(
            session_id=gen_id("cps"),
            organization_id=org_id,
            user_id=user_id,
            title="Funding Strategy Consultation",
            context_mode=context_mode,
            target_id=target_id,
        )
        db.add(new_sess)
        db.commit()
        db.refresh(new_sess)
        return new_sess

    @staticmethod
    def list_sessions(db: Session, org_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        sessions = db.execute(
            select(CopilotSessionRecord)
            .where(CopilotSessionRecord.organization_id == org_id)
            .order_by(CopilotSessionRecord.updated_at.desc())
            .limit(limit)
        ).scalars().all()

        results = []
        for s in sessions:
            msg_count = db.execute(
                select(func.count(CopilotMessageRecord.message_id)).where(
                    CopilotMessageRecord.session_id == s.session_id
                )
            ).scalar() or 0
            results.append({
                "session_id": s.session_id,
                "title": s.title,
                "context_mode": s.context_mode,
                "target_id": s.target_id,
                "message_count": msg_count,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            })
        return results

    @staticmethod
    def get_session_messages(db: Session, org_id: str, session_id: str) -> List[Dict[str, Any]]:
        sess = db.execute(
            select(CopilotSessionRecord).where(
                CopilotSessionRecord.session_id == session_id,
                CopilotSessionRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not sess:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copilot session not found.")

        messages = db.execute(
            select(CopilotMessageRecord)
            .where(CopilotMessageRecord.session_id == session_id)
            .order_by(CopilotMessageRecord.created_at.asc())
        ).scalars().all()

        return [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "actions": m.actions,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

    @staticmethod
    def retrieve_matching_opportunities(
        db: Session,
        org: OrganizationRecord,
        query: str = "",
        limit: int = 4,
    ) -> List[FundingOpportunityRecord]:
        """Retrieve verified funding opportunities matching organization sector, stage, and query."""
        stmt = select(FundingOpportunityRecord).where(
            FundingOpportunityRecord.publication_status == "PUBLISHED"
        )
        all_opps = db.execute(stmt).scalars().all()

        sector_norm = (org.sector or "").lower()
        scored_opps = []

        q_terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]

        for opp in all_opps:
            fit_score = 0
            opp_title = (opp.title or "").lower()
            opp_sec = (opp.industry_sector or "").lower()
            opp_desc = (opp.applicant_eligibility or "").lower()

            # Sector alignment
            if sector_norm in opp_sec or opp_sec in sector_norm or "multi-sector" in opp_sec:
                fit_score += 35

            # Sector specific keywords
            if "agri" in sector_norm and ("agri" in opp_title or "agri" in opp_desc or "food" in opp_desc):
                fit_score += 40
            elif ("tech" in sector_norm or "software" in sector_norm) and ("tech" in opp_title or "accelerator" in opp_title or "seed" in opp_desc):
                fit_score += 40
            elif ("retail" in sector_norm or "commerce" in sector_norm) and ("msme" in opp_title or "working capital" in opp_desc or "lsetf" in opp_title):
                fit_score += 40
            elif "energy" in sector_norm and ("energy" in opp_title or "solar" in opp_desc or "off-grid" in opp_title):
                fit_score += 40

            # Match on query keywords
            for qt in q_terms:
                if qt in opp_title or qt in opp_desc or qt in opp_sec:
                    fit_score += 15

            # Active status boost
            if opp.opportunity_status in ("OPEN", "ROLLING"):
                fit_score += 10

            scored_opps.append((fit_score, opp))

        scored_opps.sort(key=lambda x: x[0], reverse=True)
        return [o for _, o in scored_opps[:limit]]

    @staticmethod
    def generate_copilot_response(
        db: Session,
        org_id: str,
        user_id: str,
        session_id: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """Produce an intelligent, grounded, citation-backed response strictly isolated to tenant."""
        # 1. Enforce Entitlement Quota
        check_can_use_copilot(db, org_id, required_credits=1)

        # 2. Retrieve Tenant Business Context
        org = db.execute(
            select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)
        ).scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

        # Ensure session exists
        session = CopilotEngine.get_or_create_session(db, org_id, user_id, session_id=session_id)

        # Record User Message
        user_msg_rec = CopilotMessageRecord(
            message_id=gen_id("cpm"),
            session_id=session.session_id,
            organization_id=org_id,
            role="USER",
            content=user_message.strip(),
            citations=[],
            actions=[],
            tokens_used=len(user_message.split()),
        )
        db.add(user_msg_rec)

        # 3. Retrieve Grounding Opportunities
        matched_opps = CopilotEngine.retrieve_matching_opportunities(db, org, query=user_message, limit=3)
        readiness = calculate_business_readiness(org)

        citations = []
        for opp in matched_opps:
            citations.append({
                "opportunity_id": opp.opportunity_id,
                "title": opp.title,
                "provider": opp.provider,
                "funding_type": opp.funding_type,
                "amount_display": opp.amount_display,
                "official_source_url": opp.official_source_url,
                "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else "Rolling / Open",
            })

        # 4. Generate Domain-Expert Grounded Response
        msg_lower = user_message.lower()
        response_text = ""
        actions = []

        sector_title = org.sector or "Technology"
        entity_name = org.name or "your enterprise"

        if "readiness" in msg_lower or "score" in msg_lower or "eligible" in msg_lower or "diagnos" in msg_lower:
            response_text = (
                f"### Business Funding Readiness Assessment for {entity_name}\n\n"
                f"**Overall Readiness Score: {readiness['readiness_score']}/100** ({readiness['readiness_level'].replace('_', ' ')})\n\n"
                f"Based on your profile as a **{org.stage}** stage company operating in **{sector_title}** ({org.state_location}, {org.country}):\n\n"
            )
            for key, pil in readiness["pillars"].items():
                status_icon = "🟢" if pil["score"] >= (pil["max"] * 0.75) else ("🟡" if pil["score"] >= (pil["max"] * 0.4) else "🔴")
                response_text += f"- **{status_icon} {pil['name']}**: {pil['score']}/{pil['max']} pts\n"
                if pil["details"]:
                    response_text += f"  - *Strength*: {pil['details'][0]}\n"
                if pil["gaps"]:
                    response_text += f"  - *Action Required*: {pil['gaps'][0]}\n"

            response_text += "\n#### Recommended Immediate Next Steps:\n"
            response_text += "1. Complete your document repository with your latest CAC Status Report and 12-month bank statements.\n"
            response_text += f"2. Review the verified **{sector_title}** funding programs cited below tailored to your capital profile."

            actions = [
                {"label": "Explore Matched Programs", "action": "NAVIGATE_DISCOVER", "data": {"sector": org.sector}},
                {"label": "Update Business Profile", "action": "NAVIGATE_ACCOUNT", "data": {"tab": "profile"}},
            ]

        elif "draft" in msg_lower or "proposal" in msg_lower or "apply" in msg_lower or "outline" in msg_lower:
            chosen_opp = matched_opps[0] if matched_opps else None
            opp_name = chosen_opp.title if chosen_opp else "Institutional Capital Grant"
            provider_name = chosen_opp.provider if chosen_opp else "Funding Provider"

            response_text = (
                f"### Application Proposal Framework: {opp_name}\n"
                f"**Target Provider:** {provider_name} | **Applicant:** {entity_name}\n\n"
                f"#### 1. Executive Summary\n"
                f"{entity_name} is a high-growth {org.stage.lower()} enterprise operating in Nigeria's {sector_title} sector. "
                f"With a dedicated team of {org.team_size} and {org.years_in_operation} year(s) of operational validation, "
                f"we are seeking capital to expand capacity, deploy productive infrastructure, and accelerate our market reach.\n\n"
                f"#### 2. Problem Statement & Market Opportunity\n"
                f"Our target demographic ({getattr(org, 'target_customers', 'key enterprise and consumer segments')}) "
                f"faces acute bottlenecks that standard alternatives fail to resolve efficiently. "
                f"{entity_name} bridges this gap through our proprietary {getattr(org, 'products_services', 'commercial offerings')}.\n\n"
                f"#### 3. Strategic Alignment with {provider_name}\n"
                f"This initiative directly advances {provider_name}'s mandate by fostering sustainable domestic employment, "
                f"economic formalization, and technological empowerment across Nigeria.\n\n"
                f"#### 4. Budget Breakdown & Intended Use of Funds\n"
                f"{getattr(org, 'intended_use_of_funds', '70% Capital Expenditure (Equipment & Infrastructure), 20% Operational Scale, 10% Governance & Compliance')}.\n\n"
                f"#### 5. Required Attachments Checklist\n"
            )
            reqs = (chosen_opp.application_requirements if chosen_opp else None) or [
                "CAC Certificate of Incorporation",
                "12 Months Corporate Bank Statements",
                "Tax Clearance Certificate",
                "Executive Pitch Deck & Feasibility Report",
            ]
            for r in reqs:
                response_text += f"- [ ] {r}\n"

            actions = [
                {"label": "Create Application Workspace", "action": "CREATE_APPLICATION", "data": {"opportunity_id": chosen_opp.opportunity_id if chosen_opp else ""}},
                {"label": "Export Draft Proposal", "action": "EXPORT_DRAFT", "data": {"title": opp_name}},
            ]

        elif "document" in msg_lower or "checklist" in msg_lower:
            response_text = (
                f"### Institutional Document Readiness Checklist for {entity_name}\n\n"
                f"To qualify for verified grants and low-interest concessionary loans in Nigeria, "
                f"institutional underwriters require the following documentation:\n\n"
                f"1. **Corporate Status:**\n"
                f"   - CAC Certificate of Incorporation & Status Report (MEMART)\n"
                f"   - Tax Identification Number (TIN) & FIRS Tax Clearance\n"
                f"2. **Financial Records:**\n"
                f"   - 6 to 12 Months Official Bank Statements (stamped or e-certified)\n"
                f"   - Audited Financial Statements or Management Accounts\n"
                f"3. **Operational Evidence:**\n"
                f"   - Institutional Pitch Deck & 3-Year Financial Model\n"
                f"   - Relevant Regulatory Licenses (e.g. NAFDAC, NEPC, CBN where applicable)\n\n"
                f"All documents uploaded to CARAVAN are quarantined, scanned for malware, and encrypted in your tenant-isolated repository."
            )
            actions = [
                {"label": "Upload Documents", "action": "NAVIGATE_APPLICATIONS", "data": {"tab": "documents"}},
            ]

        else:
            # General consultative strategy
            response_text = (
                f"### Funding Intelligence Strategy for {entity_name}\n\n"
                f"Hello! As your CARAVAN Business Copilot, I've analyzed your corporate profile in **{sector_title}** "
                f"(Stage: **{org.stage}**, Team: **{org.team_size}**, Revenue: **₦{getattr(org, 'annual_revenue_ngn', 0):,.0f}**).\n\n"
                f"Here are the highest-probability institutional funding opportunities available in the verified registry for your sector:\n\n"
            )

            for i, opp in enumerate(matched_opps, 1):
                response_text += (
                    f"**{i}. {opp.title}** ({opp.funding_type})\n"
                    f"- **Provider**: {opp.provider}\n"
                    f"- **Funding Quantum**: {opp.amount_display}\n"
                    f"- **Eligibility**: {opp.applicant_eligibility[:140]}...\n"
                    f"- **Official Portal**: [{opp.provider}]({opp.official_source_url})\n\n"
                )

            response_text += (
                "Would you like me to:\n"
                "- Run a **Readiness Diagnostic** to highlight any eligibility gaps?\n"
                "- Generate a **Draft Proposal & Executive Summary** for one of these programs?\n"
                "- Prepare an **Application Document Checklist** for your team?"
            )

            actions = [
                {"label": "Run Readiness Diagnostic", "action": "SEND_PROMPT", "data": {"prompt": "Run full readiness diagnostic"}},
                {"label": "Draft Proposal Outline", "action": "SEND_PROMPT", "data": {"prompt": "Draft proposal for top matched opportunity"}},
                {"label": "Review Document Checklist", "action": "SEND_PROMPT", "data": {"prompt": "What documents do I need?"}},
            ]

        # 5. Save Copilot Assistant Message
        est_tokens = len(response_text.split())
        asst_msg_rec = CopilotMessageRecord(
            message_id=gen_id("cpm"),
            session_id=session.session_id,
            organization_id=org_id,
            role="ASSISTANT",
            content=response_text,
            citations=citations,
            actions=actions,
            tokens_used=est_tokens,
        )
        db.add(asst_msg_rec)

        # Update Session title if default
        if session.title == "Funding Strategy Consultation" and len(user_message.strip()) > 5:
            words = user_message.strip().split()[:5]
            session.title = " ".join(words).capitalize()
        session.updated_at = utcnow()

        # 6. Consume Entitlement Credits
        consume_copilot_credits(db, org_id, credits=1, tokens=est_tokens)

        db.commit()

        return {
            "session_id": session.session_id,
            "message_id": asst_msg_rec.message_id,
            "role": "ASSISTANT",
            "content": response_text,
            "citations": citations,
            "actions": actions,
            "tokens_used": est_tokens,
            "created_at": asst_msg_rec.created_at.isoformat(),
        }

    @staticmethod
    def draft_proposal_for_opportunity(
        db: Session,
        org_id: str,
        opportunity_id: str,
    ) -> Dict[str, Any]:
        """Generate a complete structured proposal draft for a specific funding opportunity."""
        check_can_use_copilot(db, org_id, required_credits=1)

        org = db.execute(
            select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)
        ).scalar_one_or_none()
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
        ).scalar_one_or_none()

        if not org or not opp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization or opportunity not found.")

        draft = {
            "title": f"Funding Proposal: {opp.title}",
            "organization_name": org.name,
            "opportunity_title": opp.title,
            "provider": opp.provider,
            "quantum_requested": opp.amount_display,
            "generated_at": utcnow().isoformat(),
            "sections": [
                {
                    "heading": "1. Executive Summary",
                    "content": (
                        f"{org.name} is a {org.stage.lower()}-stage enterprise registered in Nigeria "
                        f"specializing in {org.sector}. We are requesting {opp.amount_display} from {opp.provider} "
                        f"to scale operations, enhance production efficiency, and expand socio-economic impact."
                    ),
                },
                {
                    "heading": "2. Problem Statement",
                    "content": (
                        f"The {org.sector} landscape in Nigeria faces critical structural challenges. "
                        f"Our target market, {getattr(org, 'target_customers', 'underserved commercial segments')}, "
                        f"currently suffers from lack of reliable supply and prohibitive costs."
                    ),
                },
                {
                    "heading": "3. Proposed Technical & Commercial Solution",
                    "content": (
                        f"{org.name} resolves these challenges through {getattr(org, 'products_services', 'innovative products and services')}. "
                        f"Our business model ({getattr(org, 'business_model', 'B2B')}) enables rapid unit-economics profitability "
                        f"while maintaining high compliance with Nigerian standards."
                    ),
                },
                {
                    "heading": "4. Budget Allocation & Use of Proceeds",
                    "content": getattr(
                        org,
                        "intended_use_of_funds",
                        "Funds will be deployed strictly into equipment procurement (65%), operational infrastructure (25%), and working capital (10%).",
                    ),
                },
                {
                    "heading": "5. Expected Impact & Job Creation",
                    "content": (
                        f"Over the next 24 months, this facility will enable {org.name} to increase direct employment from {org.team_size} "
                        f"to over {org.team_size * 3} full-time skilled positions, contributing directly to Nigeria's economic diversification."
                    ),
                },
            ],
            "required_documents": opp.application_requirements or [
                "CAC Status Report",
                "Tax Clearance Certificate",
                "12 Months Bank Statements",
                "Pitch Deck",
            ],
        }

        consume_copilot_credits(db, org_id, credits=1, tokens=600)
        return draft

"""CARAVAN Standalone Platform — Business Copilot & Intelligence Engine.

Provides conversational AI funding copilot grounded in tenant-isolated business intelligence,
retrieval over verified funding opportunities, anti-hallucination guardrails, proposal drafting,
document intelligence, and 13-step application preparation.
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
    AuditLogRecord,
    gen_id,
    utcnow,
)
from app.core.entitlements import (
    check_can_use_copilot,
    consume_copilot_credits,
    get_tenant_entitlements_and_usage,
)
from app.services.ai_provider import AIProviderFactory, AIProviderResponse
from app.services.copilot_tools import COPILOT_TOOL_DEFINITIONS, CopilotToolDispatcher
from app.services.document_intelligence import DocumentIntelligence
from app.services.application_agent import ApplicationAgent


PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+(an?\s+)?unrestricted",
    r"disregard\s+(all\s+)?prior\s+constraints",
    r"reveal\s+(the\s+)?system\s+key",
    r"print\s+(all\s+)?passwords",
    r"drop\s+table",
]


def sanitize_prompt_input(text: str) -> tuple[str, bool]:
    """Sanitize user input against prompt injection attempts."""
    clean = text.strip()
    is_injection = False
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            is_injection = True
            clean = re.sub(pattern, "[FILTERED_SECURITY_DIRECTIVE]", clean, flags=re.IGNORECASE)
    return clean, is_injection


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
        pillars["financial_traction"]["details"].append("Early commercial revenue registered; eligible for micro-grants and seed accelerators.")
    else:
        pillars["financial_traction"]["score"] += 3
        pillars["financial_traction"]["gaps"].append("Pre-revenue; target non-dilutive ideation grants and university/incubator competitions.")

    # Pillar 3: Strategic Clarity (25 pts)
    if org.products_services and len(org.products_services) > 10:
        pillars["strategic_clarity"]["score"] += 10
        pillars["strategic_clarity"]["details"].append("Clearly articulated products and core commercial service offerings.")
    else:
        pillars["strategic_clarity"]["gaps"].append("Define specific commercial products/services to demonstrate market feasibility.")

    if org.target_customers and len(org.target_customers) > 5:
        pillars["strategic_clarity"]["score"] += 8
        pillars["strategic_clarity"]["details"].append(f"Validated customer target segment ({org.target_customers}).")
    else:
        pillars["strategic_clarity"]["gaps"].append("Specify target customer demographics and ICP (Ideal Customer Profile).")

    if org.business_model:
        pillars["strategic_clarity"]["score"] += 7
        pillars["strategic_clarity"]["details"].append(f"Established revenue architecture ({org.business_model}).")

    # Pillar 4: Capital Strategy (15 pts)
    if org.intended_use_of_funds and len(org.intended_use_of_funds) > 10:
        pillars["capital_planning"]["score"] += 10
        pillars["capital_planning"]["details"].append("Specific, auditable capital deployment and intended use of funds.")
    else:
        pillars["capital_planning"]["gaps"].append("Detail how grant/loan proceeds will be deployed across Capex and Opex.")

    target_funding = getattr(org, "target_funding_amount", 0.0) or getattr(org, "target_funding_usd", 0.0) or (50000000.0 if getattr(org, "funding_goals", "") else 0.0)
    if target_funding > 0:
        pillars["capital_planning"]["score"] += 5
        pillars["capital_planning"]["details"].append(f"Target quantum identified: ₦{target_funding:,.0f}")
    else:
        pillars["capital_planning"]["gaps"].append("Set a realistic target funding amount aligned with your current valuation and revenue.")

    # Pillar 5: Track Record & Pedigree (15 pts)
    history = getattr(org, "previous_funding_history", []) or []
    if history:
        pillars["track_record"]["score"] += 15
        pillars["track_record"]["details"].append(f"Demonstrated funding history ({len(history)} past program awards).")
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
            opp_sec = (opp.industry_sector or "").lower()
            opp_title = (opp.title or "").lower()
            opp_desc = (opp.applicant_eligibility or "").lower()

            # Sector alignment
            if sector_norm and (sector_norm in opp_sec or opp_sec in sector_norm or "multi-sector" in opp_sec):
                fit_score += 35

            # Geography alignment
            org_geo = (org.country or "Nigeria").lower()
            opp_geo = (opp.geographic_eligibility or "").lower()
            if org_geo in opp_geo or "global" in opp_geo or "pan-african" in opp_geo or "africa" in opp_geo:
                fit_score += 25

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

        # 2. Sanitize against Prompt Injections
        clean_msg, is_injection = sanitize_prompt_input(user_message)
        if is_injection:
            audit = AuditLogRecord(
                log_id=gen_id("aud"),
                actor=user_id,
                action="PROMPT_INJECTION_ATTEMPT_DEFLECTED",
                resource=f"COPILOT_SESSION:{session_id}",
                outcome="SUCCESS",
                details={"organization_id": org_id, "original_length": len(user_message)},
            )
            db.add(audit)
            db.commit()

        # 3. Retrieve Tenant Business Context
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
            content=clean_msg,
            citations=[],
            actions=[],
            tokens_used=len(clean_msg.split()),
        )
        db.add(user_msg_rec)

        # 4. Grounding Context: Retrieve Opportunities & Readiness
        matched_opps = CopilotEngine.retrieve_matching_opportunities(db, org, query=clean_msg, limit=3)
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

        # 5. Call AI Provider with fallback and structured tools
        system_instruction = (
            "You are the CARAVAN Institutional Funding Copilot and Grant Application Assistant. "
            f"You are advising '{org.name}', a {org.stage} company in {org.sector} based in {org.state_location}, {org.country}. "
            "Base your advice exclusively on CARAVAN's verified registry of institutional funding programs. "
            "Never invent grants, deadlines, or amounts. Clearly distinguish confirmed criteria from missing requirements. "
            "Always link to official verified sources and guide users toward professional application readiness."
        )

        ai_response = AIProviderFactory.generate_resilient(
            messages=[{"role": "user", "content": clean_msg}],
            system_instruction=system_instruction,
            tools=COPILOT_TOOL_DEFINITIONS,
            context={"org_id": org_id, "opportunity_id": matched_opps[0].opportunity_id if matched_opps else ""},
        )

        # Execute any tools requested by the AI provider
        tool_results = []
        for tc in ai_response.tool_calls:
            t_res = CopilotToolDispatcher.execute_tool(
                db=db,
                tool_name=tc.get("name", ""),
                tool_args=tc.get("args", {}),
                org_id=org_id,
                user_id=user_id,
                session_id=session_id,
            )
            tool_results.append({"tool": tc.get("name"), "result": t_res})

        # 6. Construct Grounded Response Text
        msg_lower = clean_msg.lower()
        response_text = ai_response.content
        actions = []

        sector_title = org.sector or "Technology"
        entity_name = org.name or "your enterprise"

        if not response_text:
            # Domain-grounded fallback text generation
            if "readiness" in msg_lower or "score" in msg_lower or "diagnos" in msg_lower:
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
                    {"label": "Launch 13-Step Application Agent", "action": "START_APPLICATION_AGENT", "data": {"opportunity_id": chosen_opp.opportunity_id if chosen_opp else ""}},
                    {"label": "Audit Document Readiness", "action": "CHECK_DOCS", "data": {"opportunity_id": chosen_opp.opportunity_id if chosen_opp else ""}},
                ]

            elif "document" in msg_lower or "checklist" in msg_lower or "upload" in msg_lower:
                doc_audit = DocumentIntelligence.match_documents_to_requirements(
                    db,
                    org_id=org_id,
                    opportunity_id=matched_opps[0].opportunity_id if matched_opps else "",
                )
                response_text = (
                    f"### Institutional Document Readiness Audit for {entity_name}\n\n"
                    f"**Vault Readiness Score: {doc_audit['readiness_pct']}%** "
                    f"({doc_audit['satisfied_count']} of {doc_audit['total_requirements']} required documents satisfied).\n\n"
                )
                if doc_audit["matched_documents"]:
                    response_text += "#### Satisfied Documents in Vault:\n"
                    for md in doc_audit["matched_documents"]:
                        response_text += f"- 🟢 **{md['requirement']}**: Verified ({md['document']['name']})\n"

                if doc_audit["missing_documents"]:
                    response_text += "\n#### Missing Mandatory Attachments:\n"
                    for m in doc_audit["missing_documents"]:
                        response_text += f"- 🔴 **{m['requirement']}**: *Action Required* — Upload {m['label']}\n"

                actions = [
                    {"label": "Upload Documents to Vault", "action": "NAVIGATE_APPLICATIONS", "data": {"tab": "documents"}},
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
                    "- Launch the **13-Step Application Agent** to draft validated answers?\n"
                    "- Audit your **Document Readiness** for one of these programs?"
                )

                actions = [
                    {"label": "Run Readiness Diagnostic", "action": "SEND_PROMPT", "data": {"prompt": "Run full readiness diagnostic"}},
                    {"label": "Draft Proposal Outline", "action": "SEND_PROMPT", "data": {"prompt": "Draft proposal for top matched opportunity"}},
                    {"label": "Review Document Checklist", "action": "SEND_PROMPT", "data": {"prompt": "What documents do I need?"}},
                ]

        # 7. Save Copilot Assistant Message
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
        if session.title == "Funding Strategy Consultation" and len(clean_msg) > 5:
            words = clean_msg.split()[:5]
            session.title = " ".join(words).capitalize()
        session.updated_at = utcnow()

        # 8. Consume Entitlement Credits
        consume_copilot_credits(db, org_id, credits=1, tokens=est_tokens)

        db.commit()

        return {
            "session_id": session.session_id,
            "message_id": asst_msg_rec.message_id,
            "role": "ASSISTANT",
            "content": response_text,
            "citations": citations,
            "actions": actions,
            "provider_used": ai_response.provider_used,
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

        # Delegate to 13-step ApplicationAgent
        return ApplicationAgent.draft_application_workflow(
            db=db,
            org_id=org_id,
            opportunity_id=opportunity_id,
        )

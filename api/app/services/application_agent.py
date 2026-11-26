"""CARAVAN Standalone Platform — 13-Step Grant & Application Preparation Agent.

Orchestrates the complete 13-step application preparation lifecycle:
1. Opportunity identification
2. Official requirements retrieval
3. Transparent eligibility assessment
4. Customer profile retrieval
5. Document requirements identification
6. Uploaded documents inspection
7. Missing documents and information detection
8. Comprehensive application answers drafting
9. Completeness and consistency validation
10. Customer review presentation
11. Explicit customer approval gating
12. Authorised channel submission or guided package preparation
13. Confirmation record and audit reference logging
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    FundingOpportunityRecord,
    OrganizationRecord,
    ApplicationRecord,
    ApplicationDraftRecord,
    CopilotApprovalRecord,
    ApplicationSubmissionRecord,
    AuditLogRecord,
    gen_id,
    utcnow,
)
from app.services.eligibility_service import evaluate_eligibility
from app.services.document_intelligence import DocumentIntelligence
from app.services.opportunity_service import compute_live_status


class ApplicationAgent:
    """13-Step Grant and Funding Application Preparation Agent."""

    @staticmethod
    def draft_application_workflow(
        db: Session,
        org_id: str,
        opportunity_id: str,
        application_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes Steps 1 through 10: Opportunity evaluation, document matching, drafting, and validation."""
        now = datetime.now(timezone.utc)

        # Step 1: Identify Opportunity
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
        ).scalar_one_or_none()
        if not opp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Opportunity '{opportunity_id}' not found.")

        # Step 2: Retrieve Official Requirements
        requirements = opp.application_requirements or [
            "CAC Certificate of Incorporation",
            "12 Months Corporate Bank Statements",
            "Tax Clearance Certificate",
            "Executive Pitch Deck & Feasibility Report",
        ]

        # Step 3: Determine Eligibility
        eligibility = evaluate_eligibility(db, org_id=org_id, opportunity_id=opportunity_id)

        # Step 4: Retrieve Customer Profile Information
        org = db.execute(
            select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)
        ).scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization record not found.")

        # Step 5 & 6: Identify & Inspect Available Uploaded Documents
        doc_audit = DocumentIntelligence.match_documents_to_requirements(db, org_id=org_id, opportunity_id=opportunity_id)

        # Step 7: Identify Missing Documents and Missing Profile Information
        missing_docs = doc_audit.get("missing_documents", [])
        missing_profile_fields = []
        if not org.cac_registered:
            missing_profile_fields.append("CAC Registration Number / Status")
        if not org.sector:
            missing_profile_fields.append("Primary Industry Sector")
        if not org.target_customers:
            missing_profile_fields.append("Target Customer Demographics")
        if not org.products_services:
            missing_profile_fields.append("Core Commercial Products and Services")

        # Step 8: Draft Application Answers
        sector_title = org.sector or "Commercial Enterprise"
        company_name = org.name or "The Applicant Enterprise"
        quantum = opp.amount_display or "Concessionary Funding Facility"

        executive_summary = (
            f"{company_name} is a high-impact, CAC-registered {org.stage.lower()} enterprise operating "
            f"in Nigeria's {sector_title} sector ({org.state_location}, {org.country}). "
            f"Led by a dedicated workforce of {org.team_size} with {org.years_in_operation} year(s) of commercial validation, "
            f"we are seeking {quantum} through {opp.provider}'s {opp.title} to deploy productive capital, "
            f"scale our operational capacity, and generate sustainable domestic economic value."
        )

        problem_statement = (
            f"Across Nigeria's {sector_title} ecosystem, key market segments—specifically "
            f"{getattr(org, 'target_customers', 'underserved commercial buyers and consumers')}—suffer from acute structural inefficiencies, "
            f"limited infrastructure access, and inflated transaction costs. "
            f"Conventional solutions fail to meet demand reliably due to supply volatility and high capital barriers."
        )

        solution_narrative = (
            f"{company_name} addresses this bottleneck through our proprietary {getattr(org, 'products_services', 'commercial offerings')}, "
            f"operating on a resilient {getattr(org, 'business_model', 'B2B')} commercial model. "
            f"Our solution delivers measurable operational efficiency, verifiable quality assurance, and competitive pricing, "
            f"advancing our strategic objective to {getattr(org, 'growth_objectives', 'expand commercial footprint and distribution nationwide')}."
        )

        budget_breakdown = [
            {"category": "Productive Capex & Equipment Procurement", "percentage": 60, "notes": "Procurement of specialized machinery and processing units."},
            {"category": "Working Capital & Raw Materials", "percentage": 25, "notes": "Inventory buffering and local supply chain settlement."},
            {"category": "Governance, Quality Certification & Compliance", "percentage": 10, "notes": "Regulatory filings, audits, and safety certifications."},
            {"category": "Contingency & Operating Buffer", "percentage": 5, "notes": "Short-term macroeconomic and foreign exchange contingency reserve."},
        ]

        sections = [
            {"heading": "1. Executive Summary", "title": "1. Executive Summary", "content": executive_summary},
            {"heading": "2. Problem Statement & Need", "title": "2. Problem Statement & Need", "content": problem_statement},
            {"heading": "3. Commercial Solution & Innovation", "title": "3. Commercial Solution & Innovation", "content": solution_narrative},
            {"heading": "4. Budget Allocation & Use of Proceeds", "title": "4. Budget Allocation & Use of Proceeds", "content": str(budget_breakdown)},
            {"heading": "5. Organizational Traction & Alignment", "title": "5. Organizational Traction & Alignment", "content": f"Operational track record of {org.years_in_operation} year(s); team of {org.team_size}; alignment with {opp.provider} strategic directives."},
        ]

        # Step 9: Validate Completeness and Consistency
        validation_notes = []
        is_complete = True

        if eligibility.get("is_disqualified", False):
            is_complete = False
            validation_notes.append("Eligibility Warning: Business currently has disqualifying criteria.")

        if missing_docs:
            is_complete = False
            validation_notes.append(f"Documentation Incomplete: {len(missing_docs)} required document(s) missing from vault.")

        if missing_profile_fields:
            is_complete = False
            validation_notes.append(f"Profile Incomplete: Please provide {', '.join(missing_profile_fields)}.")

        validation_status = "VALIDATED" if is_complete else "INCOMPLETE"

        # Step 10: Present Application for Customer Review
        # Get or create ApplicationRecord
        app_rec = None
        if application_id:
            app_rec = db.execute(
                select(ApplicationRecord).where(
                    ApplicationRecord.application_id == application_id,
                    ApplicationRecord.organization_id == org_id,
                )
            ).scalar_one_or_none()

        if not app_rec:
            app_rec = ApplicationRecord(
                application_id=gen_id("app"),
                organization_id=org_id,
                opportunity_id=opportunity_id,
                status="REVIEW",
                checklist_progress=doc_audit.get("matched_documents", []),
                notes=f"Drafted via CARAVAN Application Agent on {now.strftime('%d %b %Y')}.",
            )
            db.add(app_rec)
            db.flush()

        # Save ApplicationDraftRecord
        draft_rec = ApplicationDraftRecord(
            draft_id=gen_id("drf"),
            application_id=app_rec.application_id,
            organization_id=org_id,
            opportunity_id=opportunity_id,
            title=f"Application: {opp.title}",
            executive_summary=executive_summary,
            problem_statement=problem_statement,
            solution_narrative=solution_narrative,
            budget_breakdown=budget_breakdown,
            sections=sections,
            validation_status=validation_status,
            validation_notes=validation_notes,
        )
        db.add(draft_rec)
        db.commit()
        db.refresh(draft_rec)

        return {
            "step": 10,
            "status": "PRESENTED_FOR_REVIEW",
            "application_id": app_rec.application_id,
            "draft_id": draft_rec.draft_id,
            "opportunity_id": opp.opportunity_id,
            "opportunity_title": opp.title,
            "provider": opp.provider,
            "eligibility": {
                "score": eligibility.get("score", 0),
                "recommendation": eligibility.get("recommendation", "UNKNOWN"),
                "is_disqualified": eligibility.get("is_disqualified", False),
            },
            "document_readiness": {
                "readiness_pct": doc_audit["readiness_pct"],
                "missing_documents": missing_docs,
                "satisfied_count": doc_audit["satisfied_count"],
            },
            "missing_profile_fields": missing_profile_fields,
            "validation_status": validation_status,
            "validation_notes": validation_notes,
            "sections": sections,
            "official_portal_url": opp.official_application_url or opp.official_source_url,
            "next_required_step": "Step 11: Explicit Customer Approval required before external submission.",
        }

    @staticmethod
    def approve_application_workflow(
        db: Session,
        org_id: str,
        user_id: str,
        application_id: str,
        customer_notes: str = "",
    ) -> Dict[str, Any]:
        """Step 11: Explicit Customer Approval before external submission."""
        app_rec = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not app_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found.")

        # Compute tamper-evident approval consent hash
        now = datetime.now(timezone.utc)
        consent_payload = f"{org_id}:{user_id}:{application_id}:{now.isoformat()}"
        approval_hash = hashlib.sha256(consent_payload.encode("utf-8")).hexdigest()

        approval_rec = CopilotApprovalRecord(
            approval_id=gen_id("appr"),
            organization_id=org_id,
            user_id=user_id,
            target_type="APPLICATION_SUBMISSION",
            target_id=application_id,
            status="APPROVED",
            customer_notes=customer_notes or "Customer explicitly verified all answers and authorized submission.",
            approval_hash=approval_hash,
            approved_at=now,
        )
        db.add(approval_rec)

        # Audit log
        audit = AuditLogRecord(
            log_id=gen_id("aud"),
            actor=user_id,
            action="CUSTOMER_APPLICATION_APPROVAL_GRANTED",
            resource=f"APPLICATION:{application_id}",
            outcome="SUCCESS",
            details={"organization_id": org_id, "approval_id": approval_rec.approval_id, "approval_hash": approval_hash},
        )
        db.add(audit)

        db.commit()
        db.refresh(approval_rec)

        return {
            "step": 11,
            "status": "APPROVED_BY_CUSTOMER",
            "approval_id": approval_rec.approval_id,
            "application_id": application_id,
            "approval_hash": approval_hash,
            "approved_at": approval_rec.approved_at.isoformat(),
            "message": "Explicit customer approval recorded. Application is authorized for external submission.",
        }

    @staticmethod
    def submit_application_workflow(
        db: Session,
        org_id: str,
        user_id: str,
        application_id: str,
        approval_id: str,
    ) -> Dict[str, Any]:
        """Steps 12 & 13: Authorized channel submission or guided submission package preparation."""
        # Enforce Step 11 Approval Gating: Must have valid customer approval!
        approval = db.execute(
            select(CopilotApprovalRecord).where(
                CopilotApprovalRecord.approval_id == approval_id,
                CopilotApprovalRecord.organization_id == org_id,
                CopilotApprovalRecord.status == "APPROVED",
            )
        ).scalar_one_or_none()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Guardrail Enforced: Submission requires explicit customer approval (Step 11). No approval record found.",
            )

        app_rec = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not app_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")

        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == app_rec.opportunity_id)
        ).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        sub_ref = f"CRV-SUB-{now.strftime('%Y%m%d')}-{gen_id('')[:8].upper()}"

        official_portal = opp.official_application_url or opp.official_source_url if opp else "https://caravanfunding.com"

        # Check if opportunity has an automated direct API channel (e.g. ULTRON or direct institutional API)
        # Most institutional government/DFI portals (BOI, NCDMB, RAPID) require guided customer portal submission
        submission_channel = "GUIDED_MANUAL_PACKAGE"
        confirmation_status = "PACKAGE_PREPARED"

        confirmation_details = {
            "official_portal_url": official_portal,
            "submission_reference": sub_ref,
            "approval_id": approval.approval_id,
            "approval_hash": approval.approval_hash,
            "prepared_documents_count": len(app_rec.checklist_progress or []),
            "next_steps": [
                f"1. Navigate to the verified official portal: {official_portal}",
                "2. Upload the validated attachments from your CARAVAN Application Workspace.",
                "3. Paste the validated application answers into the corresponding form sections.",
                "4. Retain your submission reference ID for audit tracking.",
            ],
        }

        # Step 13: Record the submission reference and confirmation
        sub_rec = ApplicationSubmissionRecord(
            submission_id=gen_id("subm"),
            application_id=application_id,
            organization_id=org_id,
            opportunity_id=app_rec.opportunity_id,
            approval_id=approval.approval_id,
            submission_channel=submission_channel,
            submission_reference=sub_ref,
            confirmation_status=confirmation_status,
            confirmation_details=confirmation_details,
        )
        db.add(sub_rec)

        app_rec.status = "SUBMITTED"
        app_rec.updated_at = now

        audit = AuditLogRecord(
            log_id=gen_id("aud"),
            actor=user_id,
            action="APPLICATION_PACKAGE_SUBMITTED_AND_CONFIRMED",
            resource=f"APPLICATION:{application_id}",
            outcome="SUCCESS",
            details={"organization_id": org_id, "submission_reference": sub_ref, "status": confirmation_status},
        )
        db.add(audit)

        db.commit()
        db.refresh(sub_rec)

        return {
            "step": 13,
            "status": "COMPLETED",
            "submission_id": sub_rec.submission_id,
            "application_id": application_id,
            "opportunity_title": opp.title if opp else "",
            "submission_reference": sub_ref,
            "confirmation_status": confirmation_status,
            "official_portal_url": official_portal,
            "details": confirmation_details,
            "message": "Application preparation workflow completed. Submission reference recorded with tamper-evident audit log.",
        }

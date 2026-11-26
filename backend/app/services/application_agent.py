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
11. Explicit customer approval gating (tied to exact draft content hash)
12. Authorised channel submission or guided package preparation
13. Confirmation record and audit reference logging

Lifecycle statuses strictly separated:
- DRAFTED
- INCOMPLETE
- READY_FOR_REVIEW
- APPROVED_BY_CUSTOMER
- PACKAGE_PREPARED
- SUBMITTED_EXTERNALLY (only if authorized API exists)
- CONFIRMED_BY_PROVIDER
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, update
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


def _compute_draft_hash(title: str, exec_summary: str, problem: str, solution: str, sections: Any) -> str:
    """Computes a SHA-256 tamper-evident hash of the exact draft contents."""
    content_payload = f"{title}:{exec_summary}:{problem}:{solution}:{str(sections)}"
    return hashlib.sha256(content_payload.encode("utf-8")).hexdigest()


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

        # STRICT LIFECYCLE SEPARATION: INCOMPLETE vs READY_FOR_REVIEW
        validation_status = "READY_FOR_REVIEW" if is_complete else "INCOMPLETE"
        workflow_status = "READY_FOR_REVIEW" if is_complete else "INCOMPLETE"

        # Step 10: Present Application for Customer Review or Flag Incomplete
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
                status=workflow_status,
                checklist_progress=doc_audit.get("matched_documents", []),
                notes=f"Drafted via CARAVAN Application Agent on {now.strftime('%d %b %Y')}.",
            )
            db.add(app_rec)
            db.flush()
        else:
            app_rec.status = workflow_status
            app_rec.checklist_progress = doc_audit.get("matched_documents", [])
            app_rec.updated_at = now

        # Save ApplicationDraftRecord
        draft_hash = _compute_draft_hash(
            title=f"Application: {opp.title}",
            exec_summary=executive_summary,
            problem=problem_statement,
            solution=solution_narrative,
            sections=sections,
        )

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

        next_step_message = (
            "Step 11: Explicit Customer Approval required before external submission package preparation."
            if is_complete
            else "Upload missing mandatory documents and complete corporate profile before requesting customer approval."
        )

        return {
            "step": 10 if is_complete else 7,
            "status": workflow_status,
            "application_id": app_rec.application_id,
            "draft_id": draft_rec.draft_id,
            "draft_hash": draft_hash,
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
            "next_required_step": next_step_message,
        }

    @staticmethod
    def approve_application_workflow(
        db: Session,
        org_id: str,
        user_id: str,
        application_id: str,
        customer_notes: str = "",
        force_approval_override: bool = False,
    ) -> Dict[str, Any]:
        """Step 11: Explicit Customer Approval tied directly to exact draft content hash."""
        app_rec = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not app_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found.")

        # Retrieve the latest draft for this application
        latest_draft = db.execute(
            select(ApplicationDraftRecord).where(
                ApplicationDraftRecord.application_id == application_id,
                ApplicationDraftRecord.organization_id == org_id,
            ).order_by(ApplicationDraftRecord.created_at.desc())
        ).scalars().first()

        if not latest_draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No application draft found to approve.")

        # Strict validation: INCOMPLETE drafts cannot be approved without explicit override
        if latest_draft.validation_status == "INCOMPLETE" and not force_approval_override:
            missing_reasons = "; ".join(latest_draft.validation_notes) if latest_draft.validation_notes else "Missing requirements"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot approve application: Application is INCOMPLETE ({missing_reasons}). All mandatory requirements must be satisfied first.",
            )

        # Compute content hash of the exact draft being approved
        draft_hash = _compute_draft_hash(
            title=latest_draft.title,
            exec_summary=latest_draft.executive_summary,
            problem=latest_draft.problem_statement,
            solution=latest_draft.solution_narrative,
            sections=latest_draft.sections,
        )

        # Invalidate any prior active approvals for this application
        prior_approvals = db.execute(
            select(CopilotApprovalRecord).where(
                CopilotApprovalRecord.organization_id == org_id,
                CopilotApprovalRecord.target_id == latest_draft.draft_id,
                CopilotApprovalRecord.status == "APPROVED",
            )
        ).scalars().all()
        for p in prior_approvals:
            p.status = "SUPERSEDED"

        now = datetime.now(timezone.utc)
        approval_rec = CopilotApprovalRecord(
            approval_id=gen_id("appr"),
            organization_id=org_id,
            user_id=user_id,
            target_type="APPLICATION_DRAFT",
            target_id=latest_draft.draft_id,
            status="APPROVED",
            customer_notes=customer_notes or "Customer explicitly verified all answers and authorized submission.",
            approval_hash=draft_hash,
            approved_at=now,
        )
        db.add(approval_rec)

        app_rec.status = "APPROVED_BY_CUSTOMER"
        app_rec.updated_at = now
        latest_draft.validation_status = "APPROVED_BY_CUSTOMER"
        latest_draft.updated_at = now

        # Audit log
        audit = AuditLogRecord(
            log_id=gen_id("aud"),
            actor=user_id,
            action="CUSTOMER_APPLICATION_APPROVAL_GRANTED",
            resource=f"APPLICATION:{application_id}",
            outcome="SUCCESS",
            details={
                "organization_id": org_id,
                "approval_id": approval_rec.approval_id,
                "draft_id": latest_draft.draft_id,
                "approval_hash": draft_hash,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(approval_rec)

        return {
            "step": 11,
            "status": "APPROVED_BY_CUSTOMER",
            "approval_id": approval_rec.approval_id,
            "application_id": application_id,
            "draft_id": latest_draft.draft_id,
            "approval_hash": draft_hash,
            "approved_at": approval_rec.approved_at.isoformat(),
            "message": "Explicit customer approval recorded and tied to exact draft content hash.",
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
        # 1. Enforce Approval Gating & Tenant Ownership
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
                detail="Security Guardrail Enforced: Submission requires explicit customer approval (Step 11). No valid approval record found.",
            )

        app_rec = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not app_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")

        # 2. Retrieve draft and verify approval hash integrity
        latest_draft = db.execute(
            select(ApplicationDraftRecord).where(
                ApplicationDraftRecord.application_id == application_id,
                ApplicationDraftRecord.organization_id == org_id,
            ).order_by(ApplicationDraftRecord.created_at.desc())
        ).scalars().first()

        if not latest_draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application draft record not found.")

        if latest_draft.validation_status == "INCOMPLETE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Security Guardrail Enforced: Cannot submit an INCOMPLETE application.",
            )

        # Invalidate approval if draft changed after approval was granted
        current_hash = _compute_draft_hash(
            title=latest_draft.title,
            exec_summary=latest_draft.executive_summary,
            problem=latest_draft.problem_statement,
            solution=latest_draft.solution_narrative,
            sections=latest_draft.sections,
        )

        if approval.approval_hash != current_hash:
            approval.status = "INVALIDATED_DRAFT_MODIFIED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval Invalidated: Application draft content was modified after customer approval was granted. New approval required.",
            )

        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == app_rec.opportunity_id)
        ).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        sub_ref = f"CRV-SUB-{now.strftime('%Y%m%d')}-{gen_id('')[:8].upper()}"
        official_portal = opp.official_application_url or opp.official_source_url if opp else "https://caravanfunding.com"

        # 3. Check for genuine external provider API integration:
        # Institutional Nigerian & African DFIs (Bank of Industry, RAPID, NCDMB, DBN, TEF, ABH) do NOT provide public applicant-submission APIs.
        # Therefore, we NEVER falsely claim SUBMITTED_EXTERNALLY. We accurately package and record PACKAGE_PREPARED.
        has_authorized_external_api = False

        if has_authorized_external_api:
            submission_channel = "AUTHORIZED_API"
            confirmation_status = "SUBMITTED_EXTERNALLY"
            app_status = "SUBMITTED_EXTERNALLY"
        else:
            submission_channel = "GUIDED_MANUAL_PACKAGE"
            confirmation_status = "PACKAGE_PREPARED"
            app_status = "PACKAGE_PREPARED"

        confirmation_details = {
            "official_portal_url": official_portal,
            "submission_reference": sub_ref,
            "approval_id": approval.approval_id,
            "approval_hash": approval.approval_hash,
            "prepared_documents_count": len(app_rec.checklist_progress or []),
            "submission_channel": submission_channel,
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

        app_rec.status = app_status
        app_rec.updated_at = now

        audit = AuditLogRecord(
            log_id=gen_id("aud"),
            actor=user_id,
            action="APPLICATION_PACKAGE_PREPARED_AND_CONFIRMED",
            resource=f"APPLICATION:{application_id}",
            outcome="SUCCESS",
            details={
                "organization_id": org_id,
                "submission_reference": sub_ref,
                "channel": submission_channel,
                "status": confirmation_status,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(sub_rec)

        return {
            "step": 13,
            "status": confirmation_status,
            "submission_id": sub_rec.submission_id,
            "application_id": application_id,
            "opportunity_title": opp.title if opp else "",
            "submission_reference": sub_ref,
            "confirmation_status": confirmation_status,
            "official_portal_url": official_portal,
            "details": confirmation_details,
            "message": (
                "Verified application package prepared for official portal submission. Retain reference for audit tracking."
                if confirmation_status == "PACKAGE_PREPARED"
                else "Application submitted externally via authorized provider API."
            ),
        }

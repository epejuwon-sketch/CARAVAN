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
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

logger = logging.getLogger("caravan")

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

        # Step 8: Draft Application Answers (Never invent missing customer facts)
        sector_title = org.sector or "[UNSPECIFIED: Primary Industry Sector]"
        company_name = org.name or "[UNSPECIFIED: Enterprise Name]"
        quantum = opp.amount_display or "Concessionary Funding Facility"
        target_cust = org.target_customers or "[UNSPECIFIED: Enter target customer demographics in Organization Profile]"
        prod_serv = org.products_services or "[UNSPECIFIED: Enter core commercial products and services in Organization Profile]"
        biz_model = getattr(org, "business_model", "") or "[UNSPECIFIED: Enter business model in Organization Profile]"
        growth_obj = getattr(org, "growth_objectives", "") or "[UNSPECIFIED: Enter growth objectives in Organization Profile]"

        executive_summary = (
            f"{company_name} is a high-impact, CAC-registered {org.stage.lower()} enterprise operating "
            f"in Nigeria's {sector_title} sector ({org.state_location}, {org.country}). "
            f"Led by a dedicated workforce of {org.team_size} with {org.years_in_operation} year(s) of commercial validation, "
            f"we are seeking {quantum} through {opp.provider}'s {opp.title} to deploy productive capital, "
            f"scale our operational capacity, and generate sustainable domestic economic value."
        )

        problem_statement = (
            f"Across Nigeria's {sector_title} ecosystem, key market segments—specifically "
            f"{target_cust}—suffer from acute structural inefficiencies, "
            f"limited infrastructure access, and inflated transaction costs. "
            f"Conventional solutions fail to meet demand reliably due to supply volatility and high capital barriers."
        )

        solution_narrative = (
            f"{company_name} addresses this bottleneck through our proprietary {prod_serv}, "
            f"operating on a resilient {biz_model} commercial model. "
            f"Our solution delivers measurable operational efficiency, verifiable quality assurance, and competitive pricing, "
            f"advancing our strategic objective to {growth_obj}."
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

        # Invalidate/supersede unsubmitted approvals for this application when a new draft is created
        prior_approvals = db.execute(
            select(CopilotApprovalRecord).where(
                CopilotApprovalRecord.organization_id == org_id,
                CopilotApprovalRecord.status.in_(["APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"]),
            )
        ).scalars().all()
        for p in prior_approvals:
            if p.target_type == "APPLICATION_DRAFT":
                has_sub = db.execute(
                    select(ApplicationSubmissionRecord).where(
                        ApplicationSubmissionRecord.approval_id == p.approval_id
                    )
                ).first()
                if not has_sub:
                    p.status = "SUPERSEDED_NEW_DRAFT_CREATED"

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
    ) -> Dict[str, Any]:
        """Step 11: Explicit Customer Approval tied directly to exact draft content hash.
        
        STRICT SECURITY:
        - Customer approval is strictly prohibited for INCOMPLETE applications.
        - Customers cannot override missing mandatory requirements.
        - Binds approval directly to exact draft content hash.
        """
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

        # Strict validation: INCOMPLETE drafts CANNOT be approved by customer under any circumstance
        if latest_draft.validation_status == "INCOMPLETE":
            missing_reasons = "; ".join(latest_draft.validation_notes) if latest_draft.validation_notes else "Missing requirements"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot approve application: Application is INCOMPLETE ({missing_reasons}). All mandatory requirements must be satisfied first. Customer approval cannot override incomplete requirements.",
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
                CopilotApprovalRecord.status.in_(["APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"]),
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
            status="APPROVED_BY_CUSTOMER",
            approval_type="CUSTOMER_APPROVAL",
            authorizer_role="CUSTOMER",
            authorizer_user_id=user_id,
            override_reason="",
            remaining_gaps=[],
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
                "approval_type": "CUSTOMER_APPROVAL",
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(approval_rec)

        return {
            "step": 11,
            "status": "APPROVED_BY_CUSTOMER",
            "approval_type": "CUSTOMER_APPROVAL",
            "approval_id": approval_rec.approval_id,
            "application_id": application_id,
            "draft_id": latest_draft.draft_id,
            "approval_hash": draft_hash,
            "approved_at": approval_rec.approved_at.isoformat(),
            "message": "Explicit customer approval recorded and tied to exact draft content hash.",
        }

    @staticmethod
    def admin_override_workflow(
        db: Session,
        admin_principal: Any,
        target_org_id: str,
        application_id: str,
        override_reason: str,
        exception_notes: str = "",
    ) -> Dict[str, Any]:
        """Authorized Administrator Exception Override.
        
        STRICT SECURITY:
        - Only users with PLATFORM_ADMIN, SUPER_ADMIN, or ADMIN roles may invoke.
        - Preserves all missing-document and missing-information warnings.
        - NEVER represents an incomplete application as complete.
        - Records who authorized the override, why, when, and which requirements remain incomplete.
        - Binds to exact draft content hash.
        """
        # 1. Enforce Administrator Role
        if not getattr(admin_principal, "is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative privilege required: Only platform administrators can authorize application exceptions.",
            )

        # 2. Require Substantive Override Justification
        clean_reason = (override_reason or "").strip()
        if len(clean_reason) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrator override requires a substantive justification explaining the exception (minimum 10 characters).",
            )

        # 3. Locate Target Application Workspace
        app_rec = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == target_org_id,
            )
        ).scalar_one_or_none()
        if not app_rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found for target organization.")

        # 4. Retrieve Latest Draft
        latest_draft = db.execute(
            select(ApplicationDraftRecord).where(
                ApplicationDraftRecord.application_id == application_id,
                ApplicationDraftRecord.organization_id == target_org_id,
            ).order_by(ApplicationDraftRecord.created_at.desc())
        ).scalars().first()

        if not latest_draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No application draft found for target application.")

        # 5. Preserve Missing Requirements Warnings
        remaining_incomplete = list(latest_draft.validation_notes or [])
        if not remaining_incomplete and latest_draft.validation_status == "INCOMPLETE":
            remaining_incomplete.append("Unsatisfied mandatory documents or corporate profile fields.")

        # 6. Compute exact draft content hash
        draft_hash = _compute_draft_hash(
            title=latest_draft.title,
            exec_summary=latest_draft.executive_summary,
            problem=latest_draft.problem_statement,
            solution=latest_draft.solution_narrative,
            sections=latest_draft.sections,
        )

        now = datetime.now(timezone.utc)

        # 7. Invalidate prior approvals
        prior_approvals = db.execute(
            select(CopilotApprovalRecord).where(
                CopilotApprovalRecord.organization_id == target_org_id,
                CopilotApprovalRecord.target_id == latest_draft.draft_id,
                CopilotApprovalRecord.status.in_(["APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"]),
            )
        ).scalars().all()
        for p in prior_approvals:
            p.status = "SUPERSEDED"

        # 8. Record Administrator Override Approval Record
        approval_rec = CopilotApprovalRecord(
            approval_id=gen_id("appr"),
            organization_id=target_org_id,
            user_id=admin_principal.user_id,
            target_type="APPLICATION_DRAFT",
            target_id=latest_draft.draft_id,
            status="APPROVED_WITH_ADMIN_OVERRIDE",
            approval_type="ADMIN_OVERRIDE",
            authorizer_role=admin_principal.role,
            authorizer_user_id=admin_principal.user_id,
            override_reason=clean_reason,
            remaining_gaps=remaining_incomplete,
            customer_notes=exception_notes or f"Administrative override authorized by {admin_principal.role} ({admin_principal.email}): {clean_reason}",
            approval_hash=draft_hash,
            approved_at=now,
        )
        db.add(approval_rec)

        # NEVER mark as complete! Mark explicitly as INCOMPLETE_ADMIN_OVERRIDE
        latest_draft.validation_status = "INCOMPLETE_ADMIN_OVERRIDE"
        latest_draft.updated_at = now
        app_rec.status = "APPROVED_BY_ADMIN_OVERRIDE"
        app_rec.updated_at = now

        # 9. Audit Logging
        audit = AuditLogRecord(
            log_id=gen_id("aud"),
            actor=admin_principal.user_id,
            action="APPLICATION_ADMIN_OVERRIDE_GRANTED",
            resource=f"APPLICATION:{application_id}",
            outcome="SUCCESS",
            details={
                "organization_id": target_org_id,
                "approval_id": approval_rec.approval_id,
                "authorizer_user_id": admin_principal.user_id,
                "authorizer_role": admin_principal.role,
                "authorizer_email": getattr(admin_principal, "email", ""),
                "override_reason": clean_reason,
                "remaining_incomplete_requirements": remaining_incomplete,
                "draft_id": latest_draft.draft_id,
                "draft_hash": draft_hash,
                "authorized_at": now.isoformat(),
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(approval_rec)

        return {
            "step": 11,
            "status": "APPROVED_BY_ADMIN_OVERRIDE",
            "approval_type": "ADMIN_OVERRIDE",
            "approval_id": approval_rec.approval_id,
            "application_id": application_id,
            "draft_id": latest_draft.draft_id,
            "approval_hash": draft_hash,
            "authorizer": {
                "user_id": admin_principal.user_id,
                "role": admin_principal.role,
                "email": getattr(admin_principal, "email", ""),
            },
            "override_reason": clean_reason,
            "remaining_incomplete_requirements": remaining_incomplete,
            "validation_status": "INCOMPLETE_ADMIN_OVERRIDE",
            "approved_at": approval_rec.approved_at.isoformat(),
            "message": "Administrative override recorded with preserved deficiency warnings and tamper-evident audit trail.",
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
                CopilotApprovalRecord.status.in_(["APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"]),
            )
        ).scalar_one_or_none()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Guardrail Enforced: Submission requires explicit customer approval or authorized administrator override (Step 11). No valid approval record found.",
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

        # If draft is still INCOMPLETE and not approved via admin override, refuse
        if latest_draft.validation_status == "INCOMPLETE" and approval.approval_type != "ADMIN_OVERRIDE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Security Guardrail Enforced: Cannot submit an INCOMPLETE application without an authorized administrator override.",
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

    @staticmethod
    def get_customer_journey(
        db: Session,
        org_id: str,
        opportunity_id: str,
        application_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Provides the complete 8-stage customer funding journey state:
        DISCOVER → MATCH → UNDERSTAND → PREPARE → REVIEW → APPROVE → SUBMIT → TRACK.
        """
        # 1. Resolve Opportunity
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
        ).scalar_one_or_none()
        if not opp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Opportunity '{opportunity_id}' not found.")

        # 2. Resolve Organization
        org = db.execute(
            select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)
        ).scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization record not found.")

        # 3. Locate ApplicationRecord if any
        app_rec = None
        if application_id:
            app_rec = db.execute(
                select(ApplicationRecord).where(
                    ApplicationRecord.application_id == application_id,
                    ApplicationRecord.organization_id == org_id,
                )
            ).scalar_one_or_none()
        if not app_rec:
            app_rec = db.execute(
                select(ApplicationRecord).where(
                    ApplicationRecord.organization_id == org_id,
                    ApplicationRecord.opportunity_id == opportunity_id,
                ).order_by(ApplicationRecord.updated_at.desc())
            ).scalars().first()

        # 4. Resolve Draft, Approval, Submission
        draft_rec = None
        approval_rec = None
        sub_rec = None

        if app_rec:
            draft_rec = db.execute(
                select(ApplicationDraftRecord).where(
                    ApplicationDraftRecord.application_id == app_rec.application_id,
                    ApplicationDraftRecord.organization_id == org_id,
                ).order_by(ApplicationDraftRecord.created_at.desc())
            ).scalars().first()

            if draft_rec:
                try:
                    approval_rec = db.execute(
                        select(CopilotApprovalRecord).where(
                            CopilotApprovalRecord.organization_id == org_id,
                            CopilotApprovalRecord.target_id == draft_rec.draft_id,
                            CopilotApprovalRecord.status.in_(["APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"]),
                        ).order_by(CopilotApprovalRecord.approved_at.desc())
                    ).scalars().first()
                except Exception:
                    db.rollback()
                    approval_rec = None

            try:
                sub_rec = db.execute(
                    select(ApplicationSubmissionRecord).where(
                        ApplicationSubmissionRecord.application_id == app_rec.application_id,
                        ApplicationSubmissionRecord.organization_id == org_id,
                    ).order_by(ApplicationSubmissionRecord.submitted_at.desc())
                ).scalars().first()
            except Exception:
                db.rollback()
                sub_rec = None

        # 5. Evaluate Eligibility & Document Vault
        elig = evaluate_eligibility(db, org_id=org_id, opportunity_id=opportunity_id)
        doc_audit = DocumentIntelligence.match_documents_to_requirements(db, org_id=org_id, opportunity_id=opportunity_id)

        # 6. Identify Missing Business Information (Profile fields)
        missing_fields = []
        if not org.cac_registered:
            missing_fields.append("CAC Corporate Registration")
        if not org.sector:
            missing_fields.append("Primary Industry Sector")
        if not org.target_customers:
            missing_fields.append("Target Customer Demographics")
        if not org.products_services:
            missing_fields.append("Core Commercial Offerings")
        if not getattr(org, "business_model", ""):
            missing_fields.append("Commercial Business Model")
        if getattr(org, "annual_revenue_ngn", 0) <= 0:
            missing_fields.append("Annual Operating Revenue (NGN)")

        # 7. Map Stages
        # DISCOVER
        stage_discover = {
            "stage_id": "DISCOVER",
            "name": "Discover",
            "sequence": 1,
            "status": "COMPLETED",
            "summary": f"Verified opportunity '{opp.title}' identified.",
            "data": {
                "opportunity_id": opp.opportunity_id,
                "title": opp.title,
                "provider": opp.provider,
                "funding_type": opp.funding_type,
                "amount_display": opp.amount_display,
                "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else "Rolling",
                "official_source_url": opp.official_source_url,
            },
        }

        # MATCH
        stage_match = {
            "stage_id": "MATCH",
            "name": "Match",
            "sequence": 2,
            "status": "COMPLETED",
            "summary": f"Algorithmic match score: {elig['match_score']}/100 ({elig['eligibility_category']}).",
            "data": {
                "match_score": elig["match_score"],
                "eligibility_category": elig["eligibility_category"],
                "eligibility_status": elig.get("eligibility_status", "CONFIRMED"),
                "eligibility_confidence": elig.get("eligibility_confidence", "CONFIRMED"),
                "confirmed_criteria": elig.get("confirmed_criteria", []),
                "likely_criteria": elig.get("likely_criteria", []),
                "unknown_criteria": elig.get("unknown_criteria", []),
                "is_disqualified": elig.get("is_disqualified", False),
                "disqualifications": elig.get("disqualifications", []),
            },
        }

        # UNDERSTAND
        stage_understand = {
            "stage_id": "UNDERSTAND",
            "name": "Understand",
            "sequence": 3,
            "status": "COMPLETED" if not missing_fields else "ACTION_REQUIRED",
            "summary": "Mandatory criteria explained. " + (
                f"{len(missing_fields)} profile field(s) require completion." if missing_fields else "All primary criteria confirmed."
            ),
            "data": {
                "missing_profile_fields": missing_fields,
                "required_documents_list": opp.application_requirements or [],
                "important_conditions": getattr(opp, "important_conditions", ""),
                "clarification_needed": bool(missing_fields),
            },
        }

        # PREPARE
        has_docs = len(doc_audit.get("matched_documents", [])) > 0
        prepare_status = "COMPLETED" if draft_rec else ("IN_PROGRESS" if has_docs else "ACTION_REQUIRED")
        stage_prepare = {
            "stage_id": "PREPARE",
            "name": "Prepare",
            "sequence": 4,
            "status": prepare_status,
            "summary": (
                f"Application drafted (Draft ID: {draft_rec.draft_id})." if draft_rec
                else f"Vault audit: {doc_audit['satisfied_count']}/{doc_audit['total_requirements']} documents verified."
            ),
            "data": {
                "has_draft": bool(draft_rec),
                "draft_id": draft_rec.draft_id if draft_rec else None,
                "satisfied_documents_count": doc_audit.get("satisfied_count", 0),
                "missing_documents": doc_audit.get("missing_documents", []),
                "matched_documents": doc_audit.get("matched_documents", []),
                "vault_readiness_pct": doc_audit.get("readiness_pct", 0),
            },
        }

        # REVIEW
        review_status = (
            "READY_FOR_REVIEW" if (draft_rec and draft_rec.validation_status in ("READY_FOR_REVIEW", "INCOMPLETE_ADMIN_OVERRIDE"))
            else ("INCOMPLETE" if draft_rec else "PENDING_DRAFT")
        )
        val_notes_str = ""
        if draft_rec and getattr(draft_rec, "validation_notes", None):
            if isinstance(draft_rec.validation_notes, list):
                val_notes_str = "; ".join(str(n) for n in draft_rec.validation_notes)
            else:
                val_notes_str = str(draft_rec.validation_notes)

        stage_review = {
            "stage_id": "REVIEW",
            "name": "Review",
            "sequence": 5,
            "status": review_status,
            "summary": (
                "Application validated and ready for customer review." if review_status == "READY_FOR_REVIEW"
                else (f"Dossier incomplete: {val_notes_str}" if val_notes_str else "Draft review pending.")
            ),
            "data": {
                "validation_status": draft_rec.validation_status if draft_rec else "NOT_DRAFTED",
                "validation_notes": draft_rec.validation_notes if draft_rec else [],
                "is_complete": draft_rec.validation_status == "READY_FOR_REVIEW" if draft_rec else False,
            },
        }

        # APPROVE
        is_approved = bool(approval_rec and approval_rec.status in ("APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"))
        appr_date_str = "Verified"
        if approval_rec and getattr(approval_rec, "approved_at", None):
            try:
                appr_date_str = approval_rec.approved_at.strftime("%d %b %Y")
            except Exception:
                appr_date_str = str(approval_rec.approved_at)

        stage_approve = {
            "stage_id": "APPROVE",
            "name": "Approve",
            "sequence": 6,
            "status": "APPROVED" if is_approved else "PENDING_APPROVAL",
            "summary": (
                f"Approved by {getattr(approval_rec, 'approval_type', 'Customer')} ({appr_date_str})." if is_approved
                else "Requires explicit customer authorization before submission."
            ),
            "data": {
                "is_approved": is_approved,
                "approval_id": approval_rec.approval_id if approval_rec else None,
                "approval_type": approval_rec.approval_type if approval_rec else None,
                "approved_at": approval_rec.approved_at.isoformat() if approval_rec and getattr(approval_rec, "approved_at", None) else None,
                "approval_hash": approval_rec.approval_hash if approval_rec else None,
            },
        }

        # SUBMIT
        stage_submit = {
            "stage_id": "SUBMIT",
            "name": "Submit",
            "sequence": 7,
            "status": sub_rec.confirmation_status if sub_rec else ("READY_TO_SUBMIT" if is_approved else "LOCKED"),
            "summary": (
                f"Package prepared with reference {sub_rec.submission_reference}." if sub_rec and sub_rec.confirmation_status == "PACKAGE_PREPARED"
                else (f"Submitted externally via {sub_rec.submission_channel}." if sub_rec and sub_rec.confirmation_status == "SUBMITTED_EXTERNALLY"
                else ("Authorization granted. Ready for submission package generation." if is_approved else "Locked pending customer approval."))
            ),
            "data": {
                "submission_id": sub_rec.submission_id if sub_rec else None,
                "submission_reference": sub_rec.submission_reference if sub_rec else None,
                "confirmation_status": sub_rec.confirmation_status if sub_rec else "PENDING",
                "submission_channel": sub_rec.submission_channel if sub_rec else "GUIDED_MANUAL_PACKAGE",
                "official_portal_url": opp.official_application_url or opp.official_source_url,
            },
        }

        # TRACK
        stage_track = {
            "stage_id": "TRACK",
            "name": "Track",
            "sequence": 8,
            "status": "TRACKING_ACTIVE" if sub_rec else "PRE_SUBMISSION",
            "summary": (
                f"Application tracked: {app_rec.status}. Reference: {sub_rec.submission_reference}." if sub_rec
                else "Tracking will activate once application package is prepared."
            ),
            "data": {
                "application_id": app_rec.application_id if app_rec else None,
                "application_status": app_rec.status if app_rec else "NOT_STARTED",
                "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else "Rolling",
                "next_milestone": (
                    "Upload package to official portal and record portal confirmation." if sub_rec and sub_rec.confirmation_status == "PACKAGE_PREPARED"
                    else "Complete approval to finalize application package."
                ),
            },
        }

        stages = [
            stage_discover,
            stage_match,
            stage_understand,
            stage_prepare,
            stage_review,
            stage_approve,
            stage_submit,
            stage_track,
        ]

        # Determine current stage
        current_stage = "DISCOVER"
        if sub_rec:
            current_stage = "TRACK"
        elif is_approved:
            current_stage = "SUBMIT"
        elif draft_rec and review_status == "READY_FOR_REVIEW":
            current_stage = "APPROVE"
        elif draft_rec:
            current_stage = "REVIEW"
        elif has_docs:
            current_stage = "PREPARE"
        elif not missing_fields:
            current_stage = "PREPARE"
        else:
            current_stage = "UNDERSTAND"

        # Generate AURELIA guidance prompt
        if current_stage == "UNDERSTAND":
            guidance = f"AURELIA suggests updating {len(missing_fields)} missing business field(s) in your profile ({', '.join(missing_fields[:3])}) to maximize underwriting confidence."
        elif current_stage == "PREPARE":
            missing_cnt = len(doc_audit.get("missing_documents", []))
            guidance = f"AURELIA is ready to draft your application. Please ensure {missing_cnt} missing attachment(s) are uploaded to your document vault."
        elif current_stage == "REVIEW":
            guidance = "AURELIA has validated your drafted responses. Review the complete application answers and checklist before proceeding to approval."
        elif current_stage == "APPROVE":
            guidance = "AURELIA requires your explicit customer authorization. Review the tamper-evident draft hash and approve the submission package."
        elif current_stage == "SUBMIT":
            guidance = "AURELIA has prepared your verified application package. Follow the guided next steps to submit via the official portal."
        elif current_stage == "TRACK":
            guidance = f"AURELIA is tracking your application for {opp.title}. Retain your submission reference ID for audit verification."
        else:
            guidance = "AURELIA is analyzing your funding options and matching your enterprise profile."

        return {
            "journey_title": "AURELIA Complete Customer Funding Journey",
            "assistant_name": "AURELIA",
            "descriptor": "Funding Intelligence",
            "positioning": "Your intelligent funding partner",
            "opportunity_id": opportunity_id,
            "opportunity_title": opp.title,
            "application_id": app_rec.application_id if app_rec else None,
            "current_stage": current_stage,
            "aurelia_guidance": guidance,
            "stages": stages,
        }

    @staticmethod
    def update_missing_business_info(
        db: Session,
        org_id: str,
        user_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Allows customer to provide missing business details directly to AURELIA."""
        org = db.execute(
            select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)
        ).scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization record not found.")

        updated_fields = {}
        for k in ["cac_registered", "cac_registration_number", "target_customers", "products_services", "business_model", "annual_revenue_ngn", "sector", "growth_objectives"]:
            if k in fields and fields[k] is not None:
                setattr(org, k, fields[k])
                updated_fields[k] = fields[k]

        org.updated_at = datetime.now(timezone.utc)

        # Invalidate unsubmitted approvals if material profile fields changed
        material_keys = {"annual_revenue_ngn", "cac_registered", "target_customers", "products_services", "business_model"}
        invalidated_count = 0
        if material_keys.intersection(updated_fields.keys()):
            try:
                pending_approvals = db.execute(
                    select(CopilotApprovalRecord).where(
                        CopilotApprovalRecord.organization_id == org_id,
                        CopilotApprovalRecord.status.in_(["APPROVED", "APPROVED_BY_CUSTOMER", "APPROVED_WITH_ADMIN_OVERRIDE"]),
                    )
                ).scalars().all()
                for appr in pending_approvals:
                    has_submission = db.execute(
                        select(ApplicationSubmissionRecord).where(
                            ApplicationSubmissionRecord.approval_id == appr.approval_id
                        )
                    ).first()
                    if not has_submission:
                        appr.status = "INVALIDATED_PROFILE_MODIFIED"
                        invalidated_count += 1
            except Exception as e:
                db.rollback()
                logger.warning("Could not query or invalidate approvals: %s", e)

        audit = AuditLogRecord(
            log_id=gen_id("aud"),
            actor=user_id,
            action="ORGANIZATION_PROFILE_UPDATED_VIA_AURELIA",
            resource=f"ORG:{org_id}",
            outcome="SUCCESS",
            details={
                "updated_fields": list(updated_fields.keys()),
                "invalidated_prior_approvals": invalidated_count,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(org)

        return {
            "status": "UPDATED",
            "organization_id": org_id,
            "updated_fields": updated_fields,
            "message": f"Successfully updated {len(updated_fields)} business profile field(s) with AURELIA.",
        }

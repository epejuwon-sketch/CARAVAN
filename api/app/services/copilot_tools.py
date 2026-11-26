"""CARAVAN Standalone Platform — Structured AI Tools & Execution Dispatcher.

Defines provider-independent tool specifications and execution handlers for:
1. search_funding_opportunities
2. get_opportunity_details
3. assess_business_eligibility
4. inspect_organization_documents
5. draft_application_package
6. request_customer_approval
7. submit_application_to_channel
8. run_readiness_diagnostic
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_, and_, desc, func
from sqlalchemy.orm import Session

from app.db.models import (
    FundingOpportunityRecord,
    OrganizationRecord,
    ApplicationRecord,
    ApplicationDraftRecord,
    CopilotApprovalRecord,
    ApplicationSubmissionRecord,
    CopilotToolExecutionRecord,
    AuditLogRecord,
    gen_id,
    utcnow,
)
from app.services.opportunity_service import list_opportunities, get_opportunity_detail
from app.services.eligibility_service import evaluate_eligibility
from app.services.document_intelligence import DocumentIntelligence


# Gemini & OpenAI compatible tool schema definitions
COPILOT_TOOL_DEFINITIONS = [
    {
        "name": "search_funding_opportunities",
        "description": "Search verified funding opportunities in CARAVAN's institutional registry by keyword, sector, country, and funding type.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search terms e.g. 'solar agribusiness grant' or 'women loan'"},
                "sector": {"type": "STRING", "description": "Sector e.g. 'Agribusiness', 'Technology', 'Healthcare'"},
                "funding_type": {"type": "STRING", "description": "GRANT, LOAN, VENTURE_CAPITAL, ACCELERATOR, COMPETITION"},
                "country": {"type": "STRING", "description": "Country name e.g. 'Nigeria'"},
                "open_only": {"type": "BOOLEAN", "description": "Only return opportunities that are currently open or rolling"},
            },
        },
    },
    {
        "name": "get_opportunity_details",
        "description": "Retrieve comprehensive official details, verified criteria, and primary source links for a specific opportunity.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "opportunity_id": {"type": "STRING", "description": "Unique identifier of the opportunity (e.g. opp_...)"},
            },
            "required": ["opportunity_id"],
        },
    },
    {
        "name": "assess_business_eligibility",
        "description": "Assess whether the customer's organization qualifies for a specific funding opportunity using verified criteria.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "opportunity_id": {"type": "STRING", "description": "The opportunity ID to evaluate against"},
            },
            "required": ["opportunity_id"],
        },
    },
    {
        "name": "inspect_organization_documents",
        "description": "Audit the customer's uploaded documentation repository against the selected opportunity's requirements checklist.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "opportunity_id": {"type": "STRING", "description": "The opportunity ID whose required document checklist to match"},
            },
            "required": ["opportunity_id"],
        },
    },
    {
        "name": "draft_application_package",
        "description": "Draft comprehensive, high-quality application answers tailored to the customer's business profile and the target grant program.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "opportunity_id": {"type": "STRING", "description": "The target funding opportunity ID"},
            },
            "required": ["opportunity_id"],
        },
    },
    {
        "name": "request_customer_approval",
        "description": "Present an application draft or submission action to the customer for explicit review and record their formal approval.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target_type": {"type": "STRING", "description": "APPLICATION_SUBMISSION or APPLICATION_DRAFT"},
                "target_id": {"type": "STRING", "description": "The application_id or draft_id"},
                "notes": {"type": "STRING", "description": "Summary of what the customer is being requested to review and approve"},
            },
            "required": ["target_type", "target_id"],
        },
    },
    {
        "name": "submit_application_to_channel",
        "description": "Submit a customer-approved application through authorized channels or generate an official guided submission package. Prohibits execution without valid approval token.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "application_id": {"type": "STRING", "description": "The application workspace ID"},
                "approval_id": {"type": "STRING", "description": "The customer approval reference ID"},
            },
            "required": ["application_id", "approval_id"],
        },
    },
    {
        "name": "run_readiness_diagnostic",
        "description": "Evaluate the customer's corporate maturity, governance, and capital readiness across 5 structural pillars.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
]


class CopilotToolDispatcher:
    """Dispatches and executes structured tools with audit logging and tenant isolation."""

    @staticmethod
    def execute_tool(
        db: Session,
        tool_name: str,
        tool_args: Dict[str, Any],
        org_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a tool function with tenant isolation and audit tracking."""
        status_flag = "SUCCESS"
        result: Dict[str, Any] = {}

        try:
            if tool_name == "search_funding_opportunities":
                result = list_opportunities(
                    db,
                    query=tool_args.get("query"),
                    category=tool_args.get("funding_type"),
                    sector=tool_args.get("sector"),
                    geo=tool_args.get("country"),
                    open_only=bool(tool_args.get("open_only", False)),
                    limit=5,
                )

            elif tool_name == "get_opportunity_details":
                opp_id = tool_args.get("opportunity_id", "")
                result = get_opportunity_detail(db, opportunity_id=opp_id)

            elif tool_name == "assess_business_eligibility":
                opp_id = tool_args.get("opportunity_id", "")
                result = evaluate_eligibility(db, org_id=org_id, opportunity_id=opp_id)

            elif tool_name == "inspect_organization_documents":
                opp_id = tool_args.get("opportunity_id", "")
                result = DocumentIntelligence.match_documents_to_requirements(db, org_id=org_id, opportunity_id=opp_id)

            elif tool_name == "draft_application_package":
                from app.services.application_agent import ApplicationAgent
                opp_id = tool_args.get("opportunity_id", "")
                result = ApplicationAgent.draft_application_workflow(db, org_id=org_id, opportunity_id=opp_id)

            elif tool_name == "request_customer_approval":
                target_type = tool_args.get("target_type", "APPLICATION_SUBMISSION")
                target_id = tool_args.get("target_id", "")
                notes = tool_args.get("notes", "")

                appr = CopilotApprovalRecord(
                    approval_id=gen_id("appr"),
                    organization_id=org_id,
                    user_id=user_id,
                    target_type=target_type,
                    target_id=target_id,
                    status="PENDING",
                    customer_notes=notes,
                )
                db.add(appr)
                db.commit()
                db.refresh(appr)
                result = {
                    "approval_id": appr.approval_id,
                    "target_type": appr.target_type,
                    "target_id": appr.target_id,
                    "status": "PENDING",
                    "message": "Customer approval request created. Please review and provide explicit confirmation.",
                }

            elif tool_name == "submit_application_to_channel":
                from app.services.application_agent import ApplicationAgent
                app_id = tool_args.get("application_id", "")
                appr_id = tool_args.get("approval_id", "")
                result = ApplicationAgent.submit_application_workflow(
                    db,
                    org_id=org_id,
                    user_id=user_id,
                    application_id=app_id,
                    approval_id=appr_id,
                )

            elif tool_name == "run_readiness_diagnostic":
                from app.services.copilot_service import calculate_business_readiness
                org = db.execute(select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)).scalar_one_or_none()
                if org:
                    result = calculate_business_readiness(org)
                else:
                    result = {"error": "Organization record not found."}

            else:
                status_flag = "FAILED"
                result = {"error": f"Unknown tool name: {tool_name}"}

        except Exception as exc:
            status_flag = "FAILED"
            result = {"error": str(exc)}

        # Persist tool execution record
        try:
            exec_rec = CopilotToolExecutionRecord(
                execution_id=gen_id("cte"),
                session_id=session_id,
                organization_id=org_id,
                user_id=user_id,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=result,
                status=status_flag,
            )
            db.add(exec_rec)
            db.commit()
        except Exception:
            db.rollback()

        return result

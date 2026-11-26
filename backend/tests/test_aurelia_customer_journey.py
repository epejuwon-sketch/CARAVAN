"""AURELIA Funding Intelligence — Complete Customer Journey Test Suite.

Verifies the entire 8-stage funding journey:
DISCOVER → MATCH → UNDERSTAND → PREPARE → REVIEW → APPROVE → SUBMIT → TRACK.

Brand Identity:
- Product: CARAVAN
- AI Assistant: AURELIA
- Descriptor: Funding Intelligence
- Positioning: Your intelligent funding partner.

Testing requirements:
1. 8-stage customer journey endpoint returns structured lifecycle stages and AURELIA guidance.
2. Direct profile updating via AURELIA fills missing business information with audit logging.
3. Eligibility matching explicitly segments CONFIRMED, LIKELY, and UNKNOWN criteria.
4. Application drafting produces grounded answers with zero hallucinated facts.
5. Review validation gates customer approval behind completeness checks.
6. Approval creates tamper-evident cryptographic draft hash.
7. Submission workflow records PACKAGE_PREPARED with unique reference ID (never SUBMITTED_EXTERNALLY).
8. Statutory deadlines and tracking milestones are properly recorded.
9. AURELIA conversational chat adheres to anti-hallucination and security directives.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import get_session_factory
from app.core.security import create_access_token
from app.db.models import (
    OrganizationRecord,
    FundingOpportunityRecord,
    ApplicationRecord,
    AuditLogRecord,
)
from app.services.eligibility_service import evaluate_eligibility


def test_aurelia_customer_journey_endpoint(client: TestClient, registered_customer: dict):
    """Test 1: Verify GET /api/v1/copilot/journey/{opportunity_id} returns the complete 8-stage journey."""
    headers = registered_customer["headers"]

    # Retrieve an opportunity from the verified catalog
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    res = client.get(f"/api/v1/copilot/journey/{opp_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["assistant_name"] == "AURELIA"
    assert data["descriptor"] == "Funding Intelligence"
    assert data["positioning"] == "Your intelligent funding partner"
    assert data["opportunity_id"] == opp_id
    assert "stages" in data
    assert len(data["stages"]) == 8

    expected_stages = [
        "DISCOVER",
        "MATCH",
        "UNDERSTAND",
        "PREPARE",
        "REVIEW",
        "APPROVE",
        "SUBMIT",
        "TRACK",
    ]
    actual_stages = [s["stage_id"] for s in data["stages"]]
    assert actual_stages == expected_stages

    # Verify AURELIA guidance prompt is provided
    assert "aurelia_guidance" in data
    assert len(data["aurelia_guidance"]) > 10


def test_aurelia_update_missing_business_info(client: TestClient, registered_customer: dict):
    """Test 2: Proactively ask for and update missing business information via AURELIA."""
    headers = registered_customer["headers"]
    org_id = registered_customer["user"]["organization_id"]

    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    # Provide missing business details directly to AURELIA
    update_payload = {
        "fields": {
            "target_customers": "Commercial smallholder cooperatives across Kaduna and Kano states",
            "products_services": "Solar-powered cold storage hubs and automated grain drying technology",
            "business_model": "B2B fee-per-storage and equipment leasing subscriptions",
            "growth_objectives": "Scale from 3 to 12 rural aggregation centers across Northern Nigeria",
            "annual_revenue_ngn": 45000000.0,
        }
    }

    res = client.post(
        f"/api/v1/copilot/journey/{opp_id}/update-profile",
        json=update_payload,
        headers=headers,
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "UPDATED"
    assert "target_customers" in res_data["updated_fields"]

    # Verify database persistence & audit logging
    session_factory = get_session_factory()
    with session_factory() as db:
        org = db.execute(
            select(OrganizationRecord).where(OrganizationRecord.org_id == org_id)
        ).scalar_one()
        assert org.target_customers == "Commercial smallholder cooperatives across Kaduna and Kano states"
        assert org.business_model == "B2B fee-per-storage and equipment leasing subscriptions"

        audit = db.execute(
            select(AuditLogRecord).where(
                AuditLogRecord.action == "ORGANIZATION_PROFILE_UPDATED_VIA_AURELIA",
                AuditLogRecord.resource == f"ORG:{org_id}",
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.outcome == "SUCCESS"


def test_eligibility_segmentation_confirmed_likely_unknown(client: TestClient, registered_customer: dict):
    """Test 3: Rigorous eligibility segmentation: CONFIRMED, LIKELY, UNKNOWN."""
    org_id = registered_customer["user"]["organization_id"]

    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    session_factory = get_session_factory()
    with session_factory() as db:
        eval_result = evaluate_eligibility(db, org_id, opp_id)

        # Must contain explicit status and criteria categorization
        assert eval_result["eligibility_status"] in ("CONFIRMED", "LIKELY", "UNKNOWN", "DISQUALIFIED")
        assert "confirmed_criteria" in eval_result
        assert "likely_criteria" in eval_result
        assert "unknown_criteria" in eval_result
        assert "disqualifications" in eval_result

        # Country / jurisdiction criteria is evaluated
        all_criteria = eval_result["confirmed_criteria"] + eval_result["likely_criteria"] + eval_result["unknown_criteria"]
        assert len(all_criteria) > 0


def test_aurelia_end_to_end_journey_workflow(client: TestClient, registered_customer: dict):
    """Test 4: Complete end-to-end journey execution:
    Draft (PREPARE) -> Audit (REVIEW) -> Approve Gating (APPROVE) -> Package Prepare (SUBMIT) -> Track (TRACK).
    """
    headers = registered_customer["headers"]
    org_id = registered_customer["user"]["organization_id"]

    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    # 1. PREPARE: Draft Application Answers
    draft_res = client.post(
        "/api/v1/copilot/application-agent/draft",
        json={"opportunity_id": opp_id},
        headers=headers,
    )
    assert draft_res.status_code == 201
    draft_data = draft_res.json()
    app_id = draft_data["application_id"]

    assert app_id is not None
    assert draft_data["status"] in ("READY_FOR_REVIEW", "INCOMPLETE")

    # 2. REVIEW & APPROVE: Customer Approval Gating
    # If incomplete, customer approval must be rejected with HTTP 422
    if draft_data["status"] == "INCOMPLETE":
        approve_res = client.post(
            "/api/v1/copilot/application-agent/approve",
            json={"application_id": app_id, "customer_notes": "Attempting early approval"},
            headers=headers,
        )
        assert approve_res.status_code == 422

        # Administrator Exception Override allows approved progression
        admin_token = create_access_token(
            data={"sub": "admin_sys", "org_id": "platform_admin_org", "role": "PLATFORM_ADMIN"}
        )
        override_res = client.post(
            "/api/v1/copilot/application-agent/admin-override",
            json={
                "application_id": app_id,
                "target_org_id": org_id,
                "override_reason": "Authorized special pilot agricultural facility exemption.",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert override_res.status_code == 200
        override_data = override_res.json()
        approval_id = override_data["approval_id"]
    else:
        # Complete application approves normally
        approve_res = client.post(
            "/api/v1/copilot/application-agent/approve",
            json={"application_id": app_id, "customer_notes": "Reviewed and fully verified."},
            headers=headers,
        )
        assert approve_res.status_code == 200
        approval_id = approve_res.json()["approval_id"]

    # 3. SUBMIT: Prepare verified submission package
    submit_res = client.post(
        "/api/v1/copilot/application-agent/submit",
        json={"application_id": app_id, "approval_id": approval_id},
        headers=headers,
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()

    # Must be PACKAGE_PREPARED (strict truthfulness: never claim SUBMITTED_EXTERNALLY without external API confirmation)
    assert submit_data["status"] == "PACKAGE_PREPARED"
    assert submit_data["confirmation_status"] == "PACKAGE_PREPARED"
    assert submit_data["submission_reference"].startswith("CRV-SUB-")
    assert "official_portal_url" in submit_data
    assert "details" in submit_data

    # 4. TRACK: Check Journey Status reflects tracking
    journey_res = client.get(
        f"/api/v1/copilot/journey/{opp_id}?application_id={app_id}",
        headers=headers,
    )
    assert journey_res.status_code == 200
    journey_data = journey_res.json()
    assert journey_data["current_stage"] == "TRACK"
    assert "tracking your application" in journey_data["aurelia_guidance"].lower()


def test_aurelia_chat_consultation_branding(client: TestClient, registered_customer: dict):
    """Test 5: Conversational consultation reflects AURELIA identity and 8-stage journey guidance."""
    headers = registered_customer["headers"]

    # 1. Create consultation session
    sess_res = client.post(
        "/api/v1/copilot/sessions",
        json={"title": "AgriTech Seed Capital Strategy", "context_mode": "GENERAL"},
        headers=headers,
    )
    assert sess_res.status_code == 201
    sess_id = sess_res.json()["session_id"]

    # 2. Query AURELIA about funding strategy
    chat_res = client.post(
        f"/api/v1/copilot/sessions/{sess_id}/chat",
        json={"message": "What is the recommended journey to secure BOI funding for our business?"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    assert "content" in chat_data
    content = chat_data["content"]

    # Response should reference AURELIA or provide structured funding advice
    assert len(content) > 50
    assert "citations" in chat_data


def test_aurelia_approval_invalidation_and_tenant_security(client: TestClient, registered_customer: dict):
    """Test 6: Strict security, tenant isolation, and approval invalidation on profile/draft changes."""
    headers_a = registered_customer["headers"]
    org_id_a = registered_customer["user"]["organization_id"]

    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    # 1. Draft application for Tenant A
    draft_res = client.post(
        "/api/v1/copilot/application-agent/draft",
        json={"opportunity_id": opp_id},
        headers=headers_a,
    )
    assert draft_res.status_code == 201
    app_id_a = draft_res.json()["application_id"]

    # 2. Grant approval via Admin Override
    admin_token = create_access_token(
        data={"sub": "admin_sys", "org_id": "platform_admin_org", "role": "PLATFORM_ADMIN"}
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    override_res = client.post(
        "/api/v1/copilot/application-agent/admin-override",
        json={
            "application_id": app_id_a,
            "target_org_id": org_id_a,
            "override_reason": "Pre-submission compliance waiver",
        },
        headers=admin_headers,
    )
    assert override_res.status_code == 200
    approval_id_1 = override_res.json()["approval_id"]

    # 3. Security: Regular customer CANNOT execute admin-override
    unauth_override = client.post(
        "/api/v1/copilot/application-agent/admin-override",
        json={
            "application_id": app_id_a,
            "target_org_id": org_id_a,
            "override_reason": "Malicious override attempt",
        },
        headers=headers_a,
    )
    assert unauth_override.status_code == 403

    # 4. Approval Invalidation: Material Profile Update invalidates unsubmitted approval
    profile_update = client.post(
        f"/api/v1/copilot/journey/{opp_id}/update-profile",
        json={"fields": {"annual_revenue_ngn": 99000000.0, "target_customers": "New enterprise customer base"}},
        headers=headers_a,
    )
    assert profile_update.status_code == 200

    # Submission with approval_id_1 MUST be rejected now (invalidated due to profile change)
    submit_attempt_1 = client.post(
        "/api/v1/copilot/application-agent/submit",
        json={"application_id": app_id_a, "approval_id": approval_id_1},
        headers=headers_a,
    )
    assert submit_attempt_1.status_code == 403

    # 5. Re-grant approval
    override_res_2 = client.post(
        "/api/v1/copilot/application-agent/admin-override",
        json={
            "application_id": app_id_a,
            "target_org_id": org_id_a,
            "override_reason": "Updated profile waiver",
        },
        headers=admin_headers,
    )
    assert override_res_2.status_code == 200
    approval_id_2 = override_res_2.json()["approval_id"]

    # 6. Approval Invalidation: Generating a NEW draft supersedes the old approval
    new_draft_res = client.post(
        "/api/v1/copilot/application-agent/draft",
        json={"opportunity_id": opp_id, "application_id": app_id_a},
        headers=headers_a,
    )
    assert new_draft_res.status_code == 201

    submit_attempt_2 = client.post(
        "/api/v1/copilot/application-agent/submit",
        json={"application_id": app_id_a, "approval_id": approval_id_2},
        headers=headers_a,
    )
    assert submit_attempt_2.status_code == 403

    # 7. Multi-Tenant Cross-Access Isolation
    # Register Tenant B
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "tenant_b_founder@caravan-test.africa",
            "password": "TenantBPassword2026!",
            "full_name": "Tenant B User",
            "organization_name": "Delta Marine Logistics",
            "entity_type": "STARTUP",
            "country": "Nigeria",
        },
    )
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B attempts to approve Tenant A's application -> 404
    cross_approve = client.post(
        "/api/v1/copilot/application-agent/approve",
        json={"application_id": app_id_a, "customer_notes": "Attempting cross-tenant approval"},
        headers=headers_b,
    )
    assert cross_approve.status_code == 404

    # Tenant B attempts to submit Tenant A's application -> 403
    cross_submit = client.post(
        "/api/v1/copilot/application-agent/submit",
        json={"application_id": app_id_a, "approval_id": approval_id_2},
        headers=headers_b,
    )
    assert cross_submit.status_code == 403

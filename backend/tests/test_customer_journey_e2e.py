"""CARAVAN Standalone Platform — 20-Step End-to-End Customer Journey Verification Suite.

Tests two distinct, isolated customer organizations through complete lifecycles:
- Account 1: Amaka Agro Ventures Ltd (Female-led, CAC registered, Lagos State, ₦25,000,000 revenue)
- Account 2: Kano Code Labs (Tech startup, unregistered, Kano State, pre-revenue, male-led)
"""

import io
from fastapi.testclient import TestClient


def test_complete_two_tenant_customer_journeys(client: TestClient):
    # =========================================================================
    # STEP 1: Register Account 1 (Female-Led Agri SME, ₦25m revenue)
    # =========================================================================
    acc1_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "amaka@amakaagro.ng",
            "password": "SecurePassword123!",
            "full_name": "Amaka Okonkwo",
            "organization_name": "Amaka Agro Ventures Ltd",
        },
    )
    assert acc1_reg.status_code == 201, acc1_reg.text
    token1 = acc1_reg.json()["access_token"]
    user1 = acc1_reg.json()["user"]
    org1_id = user1["organization_id"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # =========================================================================
    # STEP 2: Configure Account 1 Profile (CAC registered, Lagos, ₦25m revenue, female-led)
    # =========================================================================
    up1 = client.put(
        "/api/v1/account/organization",
        headers=headers1,
        json={
            "name": "Amaka Agro Ventures Ltd",
            "country": "Nigeria",
            "state_location": "Lagos",
            "sector": "AgriTech",
            "stage": "EARLY_GROWTH",
            "annual_revenue_ngn": 25000000.0,
            "cac_registered": True,
            "years_in_operation": 3,
            "female_led": True,
            "youth_led": True,
            "funding_goals": "Expand cold chain distribution and processing capacity.",
        },
    )
    assert up1.status_code == 200
    assert up1.json()["female_led"] is True
    assert up1.json()["annual_revenue_ngn"] == 25000000.0

    # =========================================================================
    # STEP 3: Register Account 2 (Male-Led Tech Startup, Pre-Revenue, Unregistered)
    # =========================================================================
    acc2_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ibrahim@kanocodelabs.ng",
            "password": "SecurePassword123!",
            "full_name": "Ibrahim Kano",
            "organization_name": "Kano Code Labs",
        },
    )
    assert acc2_reg.status_code == 201
    token2 = acc2_reg.json()["access_token"]
    user2 = acc2_reg.json()["user"]
    org2_id = user2["organization_id"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # =========================================================================
    # STEP 4: Configure Account 2 Profile (Unregistered, Kano, ₦0 revenue, male-led)
    # =========================================================================
    up2 = client.put(
        "/api/v1/account/organization",
        headers=headers2,
        json={
            "name": "Kano Code Labs",
            "country": "Nigeria",
            "state_location": "Kano",
            "sector": "Technology",
            "stage": "IDEA",
            "annual_revenue_ngn": 0.0,
            "cac_registered": False,
            "years_in_operation": 1,
            "female_led": False,
            "youth_led": True,
            "funding_goals": "Build cloud prototype and train initial cohorts.",
        },
    )
    assert up2.status_code == 200
    assert up2.json()["female_led"] is False
    assert up2.json()["cac_registered"] is False

    # =========================================================================
    # STEP 5: Browse Opportunities Marketplace
    # =========================================================================
    mkt_res = client.get("/api/v1/opportunities")
    assert mkt_res.status_code == 200
    opps = mkt_res.json()["opportunities"]
    assert len(opps) >= 15

    # Check that required seed opportunities exist
    titles = [o["title"] for o in opps]
    assert "BOI Guaranteed Loans for Women" in titles
    assert "GROW Accelerator by Zuri Circle Network" in titles
    assert "Young Africa Innovates — UNDP Cohort 2" in titles
    assert any("LSETF" in t for t in titles)
    assert "BOI RAPID — Renewing Hope" in titles

    # Verify Young Africa Innovates is CLOSED
    yai = next(o for o in opps if "Young Africa Innovates" in o["title"])
    assert yai["opportunity_status"] == "CLOSED"

    # Verify GROW Accelerator has mandatory fee disclosure
    grow = next(o for o in opps if "GROW Accelerator" in o["title"])
    assert "application fee of ₦25,000" in grow["important_conditions"]

    # Search by keyword
    search_res = client.get("/api/v1/opportunities?query=Women")
    assert search_res.status_code == 200
    assert any("Women" in o["title"] for o in search_res.json()["opportunities"])

    # Filter by funding type (LOAN)
    loan_res = client.get("/api/v1/opportunities?funding_type=LOAN")
    assert loan_res.status_code == 200
    for o in loan_res.json()["opportunities"]:
        assert o["funding_type"] == "LOAN"

    # Detail view
    detail_res = client.get(f"/api/v1/opportunities/{grow['opportunity_id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == grow["title"]

    # =========================================================================
    # STEP 6: Eligibility Matching for Account 1 (Amaka - Female, ₦25m, Lagos, CAC)
    # =========================================================================
    rec1 = client.get("/api/v1/eligibility/recommendations", headers=headers1)
    assert rec1.status_code == 200
    rec1_data = rec1.json()

    # Amaka should have strong matches for BOI Women, GROW, and LSETF W-Initiative
    strong_titles1 = [r["opportunity_title"] for r in rec1_data["strong_matches"]]
    assert any("Women" in t or "GROW" in t or "W-Initiative" in t for t in strong_titles1)

    # Amaka's evaluation for GROW should be STRONG (meets ₦20m and female-led)
    grow_eval1 = client.post(f"/api/v1/eligibility/assess/{grow['opportunity_id']}", headers=headers1).json()
    assert grow_eval1["recommendation_level"] in ("STRONG", "MODERATE")
    assert grow_eval1["is_disqualified"] is False

    # =========================================================================
    # STEP 7: Eligibility Matching for Account 2 (Ibrahim - Male, Kano, ₦0, No CAC)
    # =========================================================================
    rec2 = client.get("/api/v1/eligibility/recommendations", headers=headers2)
    assert rec2.status_code == 200
    rec2_data = rec2.json()

    # Ibrahim's evaluation for GROW should be INELIGIBLE with transparent reasons
    grow_eval2 = client.post(f"/api/v1/eligibility/assess/{grow['opportunity_id']}", headers=headers2).json()
    assert grow_eval2["recommendation_level"] == "INELIGIBLE"
    assert grow_eval2["is_disqualified"] is True
    # Verify transparent reasons
    disq_text = " ".join(grow_eval2["disqualifications"])
    assert "female-led" in disq_text.lower() or "women-owned" in disq_text.lower()
    assert "20,000,000" in disq_text

    # Ibrahim's evaluation for LSETF should be disqualified due to Lagos State restriction
    lsetf = next(o for o in opps if "LSETF" in o["title"])
    lsetf_eval2 = client.post(f"/api/v1/eligibility/assess/{lsetf['opportunity_id']}", headers=headers2).json()
    assert lsetf_eval2["recommendation_level"] == "INELIGIBLE"
    assert any("lagos" in d.lower() for d in lsetf_eval2["disqualifications"])

    # =========================================================================
    # STEP 8: Save Opportunities in Pipelines
    # =========================================================================
    save1 = client.post("/api/v1/saved", headers=headers1, json={"opportunity_id": grow["opportunity_id"]})
    assert save1.status_code == 201

    save2 = client.post("/api/v1/saved", headers=headers2, json={"opportunity_id": yai["opportunity_id"]})
    assert save2.status_code == 201

    # Verify Saved List Isolation
    saved_list1 = client.get("/api/v1/saved", headers=headers1).json()["saved"]
    assert len(saved_list1) == 1
    assert saved_list1[0]["opportunity_id"] == grow["opportunity_id"]

    saved_list2 = client.get("/api/v1/saved", headers=headers2).json()["saved"]
    assert len(saved_list2) == 1
    assert saved_list2[0]["opportunity_id"] == yai["opportunity_id"]

    # =========================================================================
    # STEP 9: Application Workspace Creation & Isolation
    # =========================================================================
    boi_women = next(o for o in opps if "BOI Guaranteed Loans for Women" in o["title"])
    app1 = client.post(
        "/api/v1/applications",
        headers=headers1,
        json={"opportunity_id": boi_women["opportunity_id"], "notes": "Amaka Agro BOI Women Loan Prep"},
    )
    assert app1.status_code == 201
    app1_id = app1.json()["application_id"]

    # Account 2 cannot access Account 1's application
    cross_app = client.get(f"/api/v1/applications/{app1_id}", headers=headers2)
    assert cross_app.status_code == 404

    # =========================================================================
    # STEP 10: Document Management Pipeline (Upload, Scan, Hash, Download)
    # =========================================================================
    fake_cac_cert = b"%PDF-1.4\n1 0 obj\n<< /Title (CAC Certificate Amaka Agro) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    up_doc1 = client.post(
        f"/api/v1/applications/{app1_id}/documents/upload",
        headers=headers1,
        files={"file": ("amaka_cac_cert.pdf", io.BytesIO(fake_cac_cert), "application/pdf")},
        data={"doc_type": "CERTIFICATE"},
    )
    assert up_doc1.status_code == 201
    doc1_id = up_doc1.json()["doc_id"]
    assert up_doc1.json()["sha256_hash"] is not None

    # Account 1 can download
    dl1 = client.get(f"/api/v1/applications/{app1_id}/documents/{doc1_id}/download", headers=headers1)
    assert dl1.status_code == 200
    assert dl1.content == fake_cac_cert

    # Account 2 is rejected with 404 (Cross-tenant security)
    dl2 = client.get(f"/api/v1/applications/{app1_id}/documents/{doc1_id}/download", headers=headers2)
    assert dl2.status_code == 404

    # =========================================================================
    # STEP 11: Application Checklist Progress
    # =========================================================================
    chk_res = client.patch(
        f"/api/v1/applications/{app1_id}",
        headers=headers1,
        json={"checklist_progress": [{"item": "CAC Certificate", "completed": True}]},
    )
    assert chk_res.status_code == 200
    assert chk_res.json()["checklist_progress"][0]["completed"] is True

    # =========================================================================
    # STEP 12: Application Status Progression
    # =========================================================================
    status_up = client.patch(
        f"/api/v1/applications/{app1_id}",
        headers=headers1,
        json={"status": "SUBMITTED"},
    )
    assert status_up.status_code == 200
    assert status_up.json()["status"] == "SUBMITTED"

    # =========================================================================
    # STEP 13: Subscription Pricing & Sandbox Payment
    # =========================================================================
    pricing = client.get("/api/v1/subscriptions/pricing").json()
    assert "tiers" in pricing
    assert len(pricing["tiers"]) >= 5

    # Simulate sandbox webhook upgrading Account 1 to GROWTH tier
    webhook_res = client.post(
        "/api/v1/subscriptions/webhook/paystack",
        headers={"x-paystack-signature": "sandbox-simulation"},
        json={
            "event": "charge.success",
            "data": {
                "reference": f"ref_e2e_amaka_{org1_id}",
                "amount": 2500000,
                "currency": "NGN",
                "customer": {"email": "amaka@amakaagro.ng"},
                "metadata": {"org_id": org1_id, "tier": "GROWTH"},
            },
        },
    )
    assert webhook_res.status_code == 200

    # Verify Account 1 is now on GROWTH tier
    sub1 = client.get("/api/v1/subscriptions/current", headers=headers1).json()
    assert sub1["tier"] == "GROWTH"

    # Verify Account 2 remains on FREE tier
    sub2 = client.get("/api/v1/subscriptions/current", headers=headers2).json()
    assert sub2["tier"] == "FREE"

    # =========================================================================
    # STEP 14: Customer Notifications
    # =========================================================================
    notifs1 = client.get("/api/v1/notifications", headers=headers1).json()
    assert "notifications" in notifs1
    assert len(notifs1["notifications"]) >= 1

    # =========================================================================
    # STEP 15: Customer Support Tickets
    # =========================================================================
    tkt = client.post(
        "/api/v1/support/tickets",
        headers=headers1,
        json={
            "subject": "Inquiry on BOI Women Loan Moratorium",
            "message": "Does the 12-month moratorium begin on disbursement or approval date?",
        },
    )
    assert tkt.status_code == 201
    assert tkt.json()["status"] == "OPEN"

    # =========================================================================
    # STEP 16: Account Logout & Return (Session Persistence)
    # =========================================================================
    # Simulate client clearing local credentials and re-authenticating
    login1_res = client.post(
        "/api/v1/auth/login",
        json={"email": "amaka@amakaagro.ng", "password": "SecurePassword123!"},
    )
    assert login1_res.status_code == 200
    new_token1 = login1_res.json()["access_token"]
    new_headers1 = {"Authorization": f"Bearer {new_token1}"}

    # Verify profile and organization state persists
    me1 = client.get("/api/v1/auth/me", headers=new_headers1).json()
    assert me1["email"] == "amaka@amakaagro.ng"
    assert me1["organization"]["name"] == "Amaka Agro Ventures Ltd"
    assert me1["organization"]["annual_revenue_ngn"] == 25000000.0
    assert me1["organization"]["female_led"] is True

    # Verify application workspace and uploaded documents persist across sessions
    app_recheck = client.get(f"/api/v1/applications/{app1_id}", headers=new_headers1).json()
    assert app_recheck["application_id"] == app1_id
    assert app_recheck["status"] == "SUBMITTED"
    assert len(app_recheck["documents"]) == 1
    assert app_recheck["documents"][0]["doc_id"] == doc1_id

    # =========================================================================
    # STEP 17: Strict Multi-Tenant Isolation Enforcement
    # =========================================================================
    # Account 2 attempting to view Account 1's application -> 404
    assert client.get(f"/api/v1/applications/{app1_id}", headers=headers2).status_code == 404
    # Account 2 attempting to download Account 1's private document -> 404
    assert client.get(f"/api/v1/applications/{app1_id}/documents/{doc1_id}/download", headers=headers2).status_code == 404
    # Account 2 attempting to mutate Account 1's checklist -> 404
    assert client.patch(f"/api/v1/applications/{app1_id}", headers=headers2, json={"status": "REJECTED"}).status_code == 404
    # Account 2 attempting to view Account 1's saved list -> isolated
    saved2_final = client.get("/api/v1/saved", headers=headers2).json()["saved"]
    assert all(s["opportunity_id"] != grow["opportunity_id"] for s in saved2_final)

    # =========================================================================
    # STEP 18: Password Recovery & Email Verification Lifecycle
    # =========================================================================
    # 18a. Request password recovery
    fp_res = client.post("/api/v1/auth/forgot-password", json={"email": "amaka@amakaagro.ng"})
    assert fp_res.status_code == 200
    assert fp_res.json()["success"] is True
    reset_tok = fp_res.json()["reset_token"]
    assert reset_tok is not None

    # 18b. Reset password with valid token
    rp_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_tok, "new_password": "NewSecurePassword456!"},
    )
    assert rp_res.status_code == 200
    assert rp_res.json()["success"] is True

    # 18c. Old password now rejected
    old_fail = client.post("/api/v1/auth/login", json={"email": "amaka@amakaagro.ng", "password": "SecurePassword123!"})
    assert old_fail.status_code == 401

    # 18d. New password accepted
    new_ok = client.post("/api/v1/auth/login", json={"email": "amaka@amakaagro.ng", "password": "NewSecurePassword456!"})
    assert new_ok.status_code == 200
    updated_token1 = new_ok.json()["access_token"]
    updated_headers1 = {"Authorization": f"Bearer {updated_token1}"}

    # 18e. Email verification token generation & validation
    ev_req = client.post("/api/v1/auth/request-verification", json={"email": "amaka@amakaagro.ng"})
    assert ev_req.status_code == 200
    ver_token = ev_req.json()["verification_token"]
    assert ver_token is not None

    ev_conf = client.post("/api/v1/auth/verify-email", json={"token": ver_token})
    assert ev_conf.status_code == 200
    assert ev_conf.json()["success"] is True

    # =========================================================================
    # STEP 19: NDPA / GDPR Statutory Data Export & Deletion Request
    # =========================================================================
    # 19a. Customer Data Export
    exp_res = client.get("/api/v1/account/export-data", headers=updated_headers1)
    assert exp_res.status_code == 200
    export_data = exp_res.json()
    assert export_data["export_metadata"]["compliance"] == "Nigeria Data Protection Act (NDPA 2023) & GDPR"
    assert export_data["organization"]["name"] == "Amaka Agro Ventures Ltd"
    assert len(export_data["applications"]) == 1
    assert len(export_data["documents_metadata"]) == 1
    assert export_data["documents_metadata"][0]["doc_id"] == doc1_id

    # 19b. Customer Deletion Request (Requires exact string "DELETE")
    del_bad = client.post("/api/v1/account/delete-request", headers=updated_headers1, json={"confirmation": "no"})
    assert del_bad.status_code == 400

    del_ok = client.post(
        "/api/v1/account/delete-request",
        headers=updated_headers1,
        json={"confirmation": "DELETE", "reason": "Completed grant cycle and archiving records."},
    )
    assert del_ok.status_code == 200
    assert del_ok.json()["status"] == "DELETION_SCHEDULED"
    assert del_ok.json()["retention_policy_days"] == 30

    # =========================================================================
    # STEP 20: Continuous Opportunity Discovery, Change Staging & Link Auditing
    # =========================================================================
    from app.core.security import create_access_token

    # Setup Platform Admin headers
    admin_tok = create_access_token({"sub": "admin_test", "org_id": "org_platform", "email": "admin@caravan.ng", "role": "PLATFORM_ADMIN"})
    admin_headers = {"Authorization": f"Bearer {admin_tok}"}

    # 20a. Detect changed funding terms and stage for human review
    change_staged = client.post(
        f"/api/v1/admin/opportunities/{grow['opportunity_id']}/detect-changes",
        headers=admin_headers,
        json={"amount_max": 150000.0, "important_conditions": "Revised mentor network requirements."},
    )
    assert change_staged.status_code == 200
    assert change_staged.json()["changed"] is True
    assert change_staged.json()["publication_status"] == "PENDING_REVIEW"

    # 20b. Review queue check: changed record appears in pending review
    queue_res = client.get("/api/v1/admin/opportunities/queue", headers=admin_headers)
    assert queue_res.status_code == 200
    pending_ids = [q["opportunity_id"] for q in queue_res.json()["queue"]]
    assert grow["opportunity_id"] in pending_ids

    # 20c. Human Authorized Approval: Admin approves changed terms
    appr_res = client.post(
        f"/api/v1/admin/opportunities/{grow['opportunity_id']}/approve",
        headers=admin_headers,
        json={"notes": "Verified new $150,000 ceiling against official Zuri Circle bulletin."},
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "PUBLISHED"

    # 20d. Link health verification: flag unreachable or invalid URLs
    link_audit = client.post(
        "/api/v1/admin/opportunities/verify-links",
        headers=admin_headers,
        json={"unreachable_urls": ["https://www.youngafricainnovates.ng/"]},
    )
    assert link_audit.status_code == 200
    assert link_audit.json()["flagged_count"] >= 1



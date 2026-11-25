"""CARAVAN Standalone Platform — PostgreSQL Production Readiness & Complete E2E Verification.

Tests all application workflows, database persistence, multi-tenant isolation,
payment sandbox handling, and S2S bridge against real PostgreSQL 16.
"""

from __future__ import annotations

import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import Base, reset_engine, run_migrations, get_engine, get_session_factory
from app.app_seed_helper import seed_test_database
from app.main import app


POSTGRES_TEST_URL = os.getenv(
    "TEST_POSTGRES_URL",
    "postgresql://caravan:caravan_secure_pwd_2026@localhost:5432/caravan_production"
)


import secrets

_TEST_EPHEMERAL_BRIDGE_KEY = f"test-ephemeral-{secrets.token_urlsafe(32)}"
_TEST_EPHEMERAL_JWT_KEY = f"test-jwt-{secrets.token_urlsafe(32)}"

@pytest.fixture(scope="module")
def pg_client():
    """TestClient wired directly to real PostgreSQL 16 container."""
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    os.environ["CARAVAN_ENV"] = "test"
    os.environ["JWT_SECRET_KEY"] = _TEST_EPHEMERAL_JWT_KEY
    os.environ["ULTRON_BRIDGE_API_KEY"] = _TEST_EPHEMERAL_BRIDGE_KEY
    get_settings.cache_clear()
    reset_engine()

    engine = get_engine()
    # Ensure tables exist
    run_migrations()

    session_factory = get_session_factory()
    with session_factory() as db:
        seed_test_database(db)

    with TestClient(app) as client:
        yield client

    reset_engine()
    get_settings.cache_clear()


def test_postgresql_connection_and_schema_verification(pg_client: TestClient):
    """Verify PostgreSQL 16 connection, dialect, and schema tables."""
    engine = get_engine()
    assert engine.dialect.name == "postgresql"

    with engine.connect() as conn:
        res = conn.execute(text("SELECT version();")).scalar()
        assert "PostgreSQL 16" in res

        # Verify all 12 core tables exist
        tables_res = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)).fetchall()
        table_names = {row[0] for row in tables_res}
        expected_tables = {
            "caravan_users",
            "caravan_organizations",
            "caravan_funding_opportunities",
            "caravan_eligibility_assessments",
            "caravan_applications",
            "caravan_documents",
            "caravan_saved_opportunities",
            "caravan_subscriptions",
            "caravan_payment_transactions",
            "caravan_support_tickets",
            "caravan_notifications",
            "caravan_audit_logs",
        }
        assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_postgresql_complete_customer_lifecycle_e2e(pg_client: TestClient):
    """Test full customer lifecycle on PostgreSQL:
    Register -> Login -> Org Setup -> Discover -> Filter -> Match -> Save -> Apply -> Upload Doc -> Progress -> Support.
    """
    client = pg_client
    uid = uuid.uuid4().hex[:6]
    email = f"dr.kalu.{uid}@healthai-abuja.ng"

    # 1. Register an account
    reg_payload = {
        "email": email,
        "password": "SecurePassword#2026",
        "full_name": "Dr. Chinedu Kalu",
        "organization_name": f"HealthAI Diagnostics Nigeria Ltd {uid}",
        "entity_type": "STARTUP",
        "country": "Nigeria",
        "state_location": "Abuja (FCT)",
        "sector": "HealthTech",
        "stage": "EARLY_GROWTH",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    user_info = auth_data["user"]
    org_id = user_info["organization_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify login & logout token verification
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword#2026"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["email"] == email

    # Test /me endpoint
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 3. Organization Profile Management
    org_res = client.get("/api/v1/account/organization", headers=headers)
    assert org_res.status_code == 200
    assert org_res.json()["name"] == f"HealthAI Diagnostics Nigeria Ltd {uid}"

    # Update organization annual revenue & funding goals
    update_org_res = client.put(
        "/api/v1/account/organization",
        headers=headers,
        json={
            "annual_revenue_usd": 45000.0,
            "funding_goals": "Seeking $250k seed grant/debt for AI ultrasound clinical trials in Northern Nigeria.",
            "team_size": 12,
        },
    )
    assert update_org_res.status_code == 200
    assert update_org_res.json()["annual_revenue_usd"] == 45000.0

    # 4. Discover funding opportunities
    disc_res = client.get("/api/v1/opportunities")
    assert disc_res.status_code == 200
    opps = disc_res.json()["opportunities"]
    assert len(opps) >= 12

    # 5. Apply filters
    # Filter by category GRANT
    grant_res = client.get("/api/v1/opportunities?category=GRANT")
    assert grant_res.status_code == 200
    grant_opps = grant_res.json()["opportunities"]
    assert len(grant_opps) > 0
    for o in grant_opps:
        assert o["funding_type"] == "GRANT"

    # Filter by geo Nigeria
    ng_res = client.get("/api/v1/opportunities?geo=Nigeria")
    assert ng_res.status_code == 200
    ng_opps = ng_res.json()["opportunities"]
    assert len(ng_opps) > 0

    # 6. Open an opportunity details
    target_opp = opps[0]
    opp_id = target_opp["opportunity_id"]
    detail_res = client.get(f"/api/v1/opportunities/{opp_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["opportunity_id"] == opp_id
    assert detail_res.json()["verification_status"] in {"VERIFIED", "VERIFIED_OPEN", "UPCOMING", "UPCOMING_CONFIRMED", "CLOSED"}

    # 7. Run smart eligibility matching
    match_res = client.post(
        "/api/v1/eligibility/assess",
        headers=headers,
        json={"opportunity_id": opp_id},
    )
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert 0 <= match_data["match_score"] <= 100
    assert "criteria_breakdown" in match_data

    # 8. Save opportunity to saved list
    save_res = client.post(f"/api/v1/saved/{opp_id}", headers=headers)
    assert save_res.status_code == 200
    assert save_res.json()["saved"] is True

    # Verify saved opportunity appears in list
    saved_list_res = client.get("/api/v1/saved", headers=headers)
    assert saved_list_res.status_code == 200
    saved_items = saved_list_res.json()["saved"]
    saved_opp_ids = [s["opportunity_id"] for s in saved_items]
    assert opp_id in saved_opp_ids

    # 9. Create an application
    app_create_res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "opportunity_id": opp_id,
            "notes": "Fast-track submission for Q1 2027 intake.",
        },
    )
    assert app_create_res.status_code == 201
    application_id = app_create_res.json()["application_id"]
    assert app_create_res.json()["status"] == "DRAFTING"

    # Retrieve single application workspace
    get_app_res = client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert get_app_res.status_code == 200
    assert get_app_res.json()["application_id"] == application_id

    # 10. Update application progress and stage
    app_update_res = client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={
            "status": "DOCS_COLLECTING",
            "notes": "CAC status report and clinical trial pitch deck compiled.",
        },
    )
    assert app_update_res.status_code == 200
    assert app_update_res.json()["status"] == "DOCS_COLLECTING"

    # 11. Attach document metadata
    doc_res = client.post(
        f"/api/v1/applications/{application_id}/documents",
        headers=headers,
        json={
            "name": "HealthAI_Clinical_Validation_2026.pdf",
            "doc_type": "PITCH_DECK",
            "file_size_bytes": 4512000,
        },
    )
    assert doc_res.status_code == 201
    assert doc_res.json()["name"] == "HealthAI_Clinical_Validation_2026.pdf"

    # Verify document is visible in workspace
    get_app_doc_res = client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert get_app_doc_res.status_code == 200
    assert len(get_app_doc_res.json()["documents"]) >= 1

    # 12. Support & Help Ticket
    ticket_res = client.post(
        "/api/v1/support/tickets",
        headers=headers,
        json={
            "subject": "Question on AfDB AgriPitch grant eligibility for healthcare cold-chain",
            "category": "ELIGIBILITY_INQUIRY",
            "message": "Does the cold-chain agriculture storage grant extend to dual-use pharmaceutical and food logistics?",
        },
    )
    assert ticket_res.status_code == 201
    assert ticket_res.json()["status"] == "OPEN"


def test_postgresql_multi_tenant_isolation(pg_client: TestClient):
    """Verify strict tenant isolation on PostgreSQL."""
    client = pg_client
    uid_a = uuid.uuid4().hex[:6]
    uid_b = uuid.uuid4().hex[:6]

    # Tenant A
    res_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"tenant_a_{uid_a}@org-a.com",
            "password": "Password123!",
            "full_name": "Alice Tenant A",
            "organization_name": f"Company Alpha {uid_a}",
            "entity_type": "STARTUP",
            "country": "Nigeria",
            "state_location": "Lagos",
            "sector": "FinTech",
            "stage": "SEED",
        },
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Tenant B
    res_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"tenant_b_{uid_b}@org-b.com",
            "password": "Password123!",
            "full_name": "Bob Tenant B",
            "organization_name": f"Company Beta {uid_b}",
            "entity_type": "SME",
            "country": "United Kingdom",
            "state_location": "London",
            "sector": "CleanTech",
            "stage": "EARLY_GROWTH",
        },
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant A creates application
    opp_res = client.get("/api/v1/opportunities")
    opp_id = opp_res.json()["opportunities"][0]["opportunity_id"]

    app_a = client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={
            "opportunity_id": opp_id,
            "notes": "Confidential Alpha Proposal",
        },
    ).json()
    app_a_id = app_a["application_id"]

    # Tenant B attempts to access Tenant A's application -> 404 Not Found (tenant isolated)
    leak_attempt = client.get(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert leak_attempt.status_code == 404, "Security violation: Cross-tenant application access permitted!"

    # Tenant B attempts to update Tenant A's application -> 404
    patch_attempt = client.patch(
        f"/api/v1/applications/{app_a_id}",
        headers=headers_b,
        json={"notes": "Hacked from Org B"},
    )
    assert patch_attempt.status_code == 404, "Security violation: Cross-tenant application mutation permitted!"


def test_postgresql_payment_sandbox_and_subscriptions(pg_client: TestClient):
    """Verify Paystack and Flutterwave sandbox webhook handling and subscription state transitions."""
    client = pg_client
    uid = uuid.uuid4().hex[:6]

    # Register user
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"finance.{uid}@scaleup-london.co.uk",
            "password": "Password#2026",
            "full_name": "Fiona Davies",
            "organization_name": f"ScaleUp London Ltd {uid}",
            "entity_type": "STARTUP",
            "country": "United Kingdom",
            "state_location": "London",
            "sector": "FinTech",
            "stage": "SEED",
        },
    ).json()
    token = reg["access_token"]
    org_id = reg["user"]["organization_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify initial tier is FREE
    cur_sub = client.get("/api/v1/subscriptions/current", headers=headers).json()
    assert cur_sub["tier"] == "FREE"

    # 1. Flutterwave Sandbox Webhook
    flw_tx_ref = f"flw_pg_test_{uid}"
    flw_payload = {
        "event": "charge.completed",
        "data": {
            "id": 99887711,
            "tx_ref": flw_tx_ref,
            "amount": 150000.0,
            "currency": "NGN",
            "status": "successful",
            "meta": {"org_id": org_id, "tier": "PRO"},
        },
    }
    flw_res = client.post(
        "/api/v1/subscriptions/webhook/flutterwave",
        json=flw_payload,
        headers={"verif-hash": "caravan-flw-secret-hash"},
    )
    assert flw_res.status_code == 200
    assert flw_res.json()["tier"] == "PRO"

    # Verify upgraded to PRO
    sub_pro = client.get("/api/v1/subscriptions/current", headers=headers).json()
    assert sub_pro["tier"] == "PRO"
    assert sub_pro["status"] == "ACTIVE"
    assert sub_pro["billing_provider"] == "FLUTTERWAVE"

    # 2. Duplicate webhook test (Idempotency)
    dup_res = client.post(
        "/api/v1/subscriptions/webhook/flutterwave",
        json=flw_payload,
        headers={"verif-hash": "caravan-flw-secret-hash"},
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["status"] == "ALREADY_PROCESSED"

    # 3. Paystack Sandbox Webhook upgrade to INSTITUTIONAL
    pstk_ref = f"pstk_pg_test_{uid}"
    pstk_payload = {
        "event": "charge.success",
        "data": {
            "reference": pstk_ref,
            "amount": 38000000,  # 380,000 NGN in kobo
            "currency": "NGN",
            "status": "success",
            "metadata": {"org_id": org_id, "tier": "INSTITUTIONAL"},
        },
    }
    pstk_res = client.post(
        "/api/v1/subscriptions/webhook/paystack",
        json=pstk_payload,
        headers={"x-paystack-signature": "caravan-paystack-webhook-secret"},
    )
    assert pstk_res.status_code == 200
    assert pstk_res.json()["tier"] == "INSTITUTIONAL"

    # Verify upgraded to INSTITUTIONAL
    sub_inst = client.get("/api/v1/subscriptions/current", headers=headers).json()
    assert sub_inst["tier"] == "INSTITUTIONAL"
    assert sub_inst["billing_provider"] == "PAYSTACK"


def test_postgresql_s2s_bridge_and_ultron_integration(pg_client: TestClient):
    """Verify scoped S2S Bridge telemetry and governance actions."""
    client = pg_client

    # 1. Unauthenticated or invalid key should be 401
    bad_res = client.get("/api/v1/bridge/telemetry", headers={"X-Ultron-Bridge-Key": "invalid-secret-key"})
    assert bad_res.status_code == 401

    # Missing header should be 401
    missing_res = client.get("/api/v1/bridge/telemetry")
    assert missing_res.status_code == 401

    # 2. Valid S2S key
    valid_key = _TEST_EPHEMERAL_BRIDGE_KEY
    bridge_headers = {"X-Ultron-Bridge-Key": valid_key}
    telemetry_res = client.get("/api/v1/bridge/telemetry", headers=bridge_headers)
    assert telemetry_res.status_code == 200
    telemetry = telemetry_res.json()
    assert telemetry["status"] == "HEALTHY"
    assert telemetry["funding_intelligence"]["total_opportunities"] >= 12
    assert telemetry["funding_intelligence"]["verified_count"] >= 5
    assert telemetry["funding_intelligence"]["unverified_count"] == 0
    assert telemetry["customers"]["total_users"] >= 1
    assert telemetry["customers"]["total_organizations"] >= 1

    # 3. Trigger bridge action: sweep expired deadlines
    sweep_res = client.post("/api/v1/bridge/sweep-expired", headers=bridge_headers)
    assert sweep_res.status_code == 200
    assert "swept_count" in sweep_res.json()

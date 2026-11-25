"""Test CARAVAN Business Copilot, Tenant Isolation, Grounding, and Funding Intelligence Engine."""

from fastapi.testclient import TestClient


def test_copilot_session_lifecycle_and_tenant_isolation(client: TestClient, registered_customer: dict):
    headers_a = registered_customer["headers"]

    # 1. Create Copilot session for Tenant A
    create_res = client.post(
        "/api/v1/copilot/sessions",
        json={"title": "AgriTech Seed Capital Strategy", "context_mode": "GENERAL"},
        headers=headers_a,
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["session_id"]
    assert session_id.startswith("cps_")

    # 2. List sessions
    list_res = client.get("/api/v1/copilot/sessions", headers=headers_a)
    assert list_res.status_code == 200
    sessions = list_res.json()["sessions"]
    assert any(s["session_id"] == session_id for s in sessions)

    # 3. Register Tenant B
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "healthtech_founder@caravan.org",
            "password": "Password123!Secure",
            "full_name": "Dr. Amina Yusuf",
            "organization_name": "Amina Diagnostic Health Ltd",
            "sector": "Healthcare",
            "stage": "SEED",
        },
    )
    assert reg_b.status_code == 201
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Tenant B must NOT see Tenant A's sessions
    list_b = client.get("/api/v1/copilot/sessions", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(s["session_id"] == session_id for s in list_b.json()["sessions"])

    # Tenant B cannot access Tenant A's session messages
    msg_b = client.get(f"/api/v1/copilot/sessions/{session_id}/messages", headers=headers_b)
    assert msg_b.status_code == 404


def test_copilot_chat_grounding_citations_and_usage(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # Initial credits check
    usage_init = client.get("/api/v1/subscriptions/usage", headers=headers).json()
    initial_used = usage_init["quotas"]["copilot_credits"]["used"]

    # Create session
    sess_res = client.post("/api/v1/copilot/sessions", json={}, headers=headers)
    session_id = sess_res.json()["session_id"]

    # Chat with copilot asking for agritech funding
    chat_res = client.post(
        f"/api/v1/copilot/sessions/{session_id}/chat",
        json={"message": "What verified institutional funding programs are available for our agritech venture?"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    data = chat_res.json()

    assert data["role"] == "ASSISTANT"
    assert len(data["content"]) > 100
    assert "citations" in data
    assert len(data["citations"]) > 0

    # Every citation must be a verified record with provider and URL
    first_citation = data["citations"][0]
    assert "opportunity_id" in first_citation
    assert "provider" in first_citation
    assert "official_source_url" in first_citation
    assert first_citation["official_source_url"].startswith("http")

    # Verify credit was consumed
    usage_after = client.get("/api/v1/subscriptions/usage", headers=headers).json()
    assert usage_after["quotas"]["copilot_credits"]["used"] == initial_used + 1


def test_copilot_readiness_report_and_business_intelligence_updates(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # 1. Fetch initial readiness report
    readiness_res = client.get("/api/v1/copilot/readiness-report", headers=headers)
    assert readiness_res.status_code == 200
    readiness_data = readiness_res.json()["readiness"]

    assert "readiness_score" in readiness_data
    assert "readiness_level" in readiness_data
    assert "pillars" in readiness_data
    assert "governance_and_compliance" in readiness_data["pillars"]
    assert "financial_traction" in readiness_data["pillars"]
    initial_score = readiness_data["readiness_score"]

    # 2. Update extended Business Intelligence profile in Account
    update_res = client.put(
        "/api/v1/account/organization",
        json={
            "cac_registered": True,
            "years_in_operation": 3,
            "annual_revenue_ngn": 18500000.0,
            "products_services": "Cold-chain solar storage units for post-harvest tomato farmers",
            "target_customers": "Smallholder farmers cooperatives and wholesale distributors in Northern Nigeria",
            "business_model": "B2B Hardware-as-a-Service and Lease-to-Own",
            "growth_objectives": "Expand to 15 distribution hubs across Kano, Kaduna and Plateau states",
            "intended_use_of_funds": "60% refrigeration machinery procurement, 25% IoT tracking units, 15% working capital",
            "previous_funding_history": [
                {"year": 2024, "provider": "Tony Elumelu Foundation", "amount": 5000, "type": "GRANT"}
            ],
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["readiness_score"] > initial_score

    # 3. Re-evaluate readiness report
    updated_readiness = client.get("/api/v1/copilot/readiness-report", headers=headers).json()["readiness"]
    assert updated_readiness["readiness_score"] >= 70.0


def test_copilot_proposal_drafting(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # Get a verified opportunity
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    target_opp = opps[0]

    # Generate draft proposal
    draft_res = client.post(
        "/api/v1/copilot/draft-proposal",
        json={"opportunity_id": target_opp["opportunity_id"]},
        headers=headers,
    )
    assert draft_res.status_code == 200
    draft = draft_res.json()

    assert "sections" in draft
    assert len(draft["sections"]) >= 4
    headings = [s["heading"] for s in draft["sections"]]
    assert any("Executive Summary" in h for h in headings)
    assert any("Problem Statement" in h for h in headings)
    assert any("Budget" in h for h in headings)


def test_funding_intelligence_continuous_discovery_engine(client: TestClient):
    # Register an admin user
    admin_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin_intel@caravan.org",
            "password": "AdminPassword123!",
            "full_name": "Chief Intelligence Officer",
            "organization_name": "CARAVAN Operations Admin",
            "sector": "Administration",
            "stage": "MATURE",
        },
    )
    admin_token = admin_reg.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Temporarily promote or check intelligence summary as reviewer/admin
    # Use ulton s2s bridge to elevate role to SUPER_ADMIN
    bridge_headers = {"X-Ultron-Bridge-Key": "test-ultron-s2s-bridge-key"}
    client.post(
        f"/api/v1/bridge/sync-opportunity",
        json={"title": "Dummy", "provider": "BOI", "official_source_url": "https://www.boi.ng/test"},
        headers=bridge_headers,
    )

    # Trigger intelligence discovery scan
    # Let's test DiscoveryEngine methods directly via admin endpoints
    # Register reviewer/admin
    # In test environment, let's elevate admin_reg user to SUPER_ADMIN directly in DB
    from app.db.session import get_session_factory
    from app.db.models import UserRecord
    session_factory = get_session_factory()
    with session_factory() as db:
        user = db.query(UserRecord).filter(UserRecord.email == "admin_intel@caravan.org").first()
        if user:
            user.role = "SUPER_ADMIN"
            db.commit()

    # Re-login to get updated token with SUPER_ADMIN role
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_intel@caravan.org", "password": "AdminPassword123!"},
    )
    super_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 1. Check intelligence summary
    summary_res = client.get("/api/v1/admin/intelligence/summary", headers=super_headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "total_records" in summary
    assert "monitored_sources_count" in summary
    assert summary["monitored_sources_count"] >= 5

    # 2. Trigger scan
    scan_res = client.post("/api/v1/admin/intelligence/scan-now", headers=super_headers)
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert "total_candidates" in scan_data
    assert scan_data["total_candidates"] >= 4
    assert scan_data["ingested_count"] > 0 or scan_data["duplicate_skipped_count"] > 0

    # 3. Subsequent scan triggers duplicate deduplication
    scan2_res = client.post("/api/v1/admin/intelligence/scan-now", headers=super_headers)
    assert scan2_res.status_code == 200
    assert scan2_res.json()["duplicate_skipped_count"] >= 3

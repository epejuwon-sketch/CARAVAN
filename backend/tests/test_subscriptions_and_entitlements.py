"""Test CARAVAN 6-Tier Subscription System, Central Entitlements Matrix & Quota Enforcement."""

from fastapi.testclient import TestClient


def test_six_subscription_tiers_and_features(client: TestClient):
    res = client.get("/api/v1/subscriptions/tiers")
    assert res.status_code == 200
    data = res.json()
    tier_map = {t["tier"]: t for t in data["tiers"]}

    # Verify all 6 canonical tiers are present
    assert "FREE" in tier_map
    assert "STARTER" in tier_map
    assert "GROWTH" in tier_map
    assert "PRO" in tier_map
    assert "BUSINESS" in tier_map
    assert "ENTERPRISE" in tier_map

    # Validate exact pricing
    assert tier_map["FREE"]["price_usd"] == 0.0
    assert tier_map["STARTER"]["price_usd"] == 19.0
    assert tier_map["GROWTH"]["price_usd"] == 49.0
    assert tier_map["PRO"]["price_usd"] == 99.0
    assert tier_map["BUSINESS"]["price_usd"] == 249.0


def test_usage_and_entitlements_reporting(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]
    res = client.get("/api/v1/subscriptions/usage", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["tier"] == "FREE"
    assert "quotas" in data
    assert "saved_opportunities" in data["quotas"]
    assert "active_applications" in data["quotas"]
    assert "copilot_credits" in data["quotas"]
    assert data["quotas"]["saved_opportunities"]["limit"] == 5
    assert data["quotas"]["active_applications"]["limit"] == 1
    assert data["quotas"]["copilot_credits"]["limit"] == 20


def test_saved_opportunity_quota_enforcement_and_upgrade(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # 1. Fetch available opportunities
    opps_res = client.get("/api/v1/opportunities")
    assert opps_res.status_code == 200
    opps = opps_res.json()["opportunities"]
    assert len(opps) >= 6

    # 2. Save 5 opportunities (FREE limit)
    for i in range(5):
        save_res = client.post("/api/v1/saved", json={"opportunity_id": opps[i]["opportunity_id"]}, headers=headers)
        assert save_res.status_code == 201

    # 3. 6th attempt should be blocked with 403 Forbidden
    blocked_res = client.post("/api/v1/saved", json={"opportunity_id": opps[5]["opportunity_id"]}, headers=headers)
    assert blocked_res.status_code == 403
    assert "limit reached" in blocked_res.json()["detail"].lower()

    # 4. Upgrade to STARTER via Sandbox
    upgrade_res = client.post("/api/v1/subscriptions/sandbox-upgrade", json={"tier": "STARTER"}, headers=headers)
    assert upgrade_res.status_code == 200
    assert upgrade_res.json()["tier"] == "STARTER"

    # 5. Now 6th save should succeed
    allowed_res = client.post("/api/v1/saved", json={"opportunity_id": opps[5]["opportunity_id"]}, headers=headers)
    assert allowed_res.status_code == 201
    assert allowed_res.json()["saved"] is True


def test_active_application_workspace_quota_enforcement(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    opps_res = client.get("/api/v1/opportunities")
    opps = opps_res.json()["opportunities"]

    # In clean tenant, create 1st application on FREE tier
    app1_res = client.post("/api/v1/applications", json={"opportunity_id": opps[0]["opportunity_id"]}, headers=headers)
    assert app1_res.status_code == 201

    # 2nd application creation should be blocked on FREE tier (limit = 1)
    # Check current tier
    sub_res = client.get("/api/v1/subscriptions/current", headers=headers)
    if sub_res.json()["tier"] == "FREE":
        app2_res = client.post("/api/v1/applications", json={"opportunity_id": opps[1]["opportunity_id"]}, headers=headers)
        assert app2_res.status_code == 403
        assert "workspaces limit reached" in app2_res.json()["detail"].lower()


def test_cross_tenant_billing_and_quota_isolation(client: TestClient, registered_customer: dict):
    # Customer A
    headers_a = registered_customer["headers"]

    # Register Customer B
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer_b_test@caravan.org",
            "password": "Password123!Secure",
            "full_name": "Tenant B Admin",
            "organization_name": "Tenant B Logistics Ltd",
            "sector": "Logistics & Supply Chain",
            "stage": "GROWTH",
        },
    )
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Customer A upgrades to BUSINESS
    client.post("/api/v1/subscriptions/sandbox-upgrade", json={"tier": "BUSINESS"}, headers=headers_a)
    sub_a = client.get("/api/v1/subscriptions/current", headers=headers_a).json()
    assert sub_a["tier"] == "BUSINESS"

    # Customer B must remain on FREE tier
    sub_b = client.get("/api/v1/subscriptions/current", headers=headers_b).json()
    assert sub_b["tier"] == "FREE"

    # Customer B usage quotas are independently calculated
    usage_b = client.get("/api/v1/subscriptions/usage", headers=headers_b).json()
    assert usage_b["tier"] == "FREE"
    assert usage_b["quotas"]["saved_opportunities"]["limit"] == 5

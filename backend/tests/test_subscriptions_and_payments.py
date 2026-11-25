"""Test CARAVAN Pricing Tiers & Nigerian Payment Gateway Webhooks (Paystack / Flutterwave)."""

from fastapi.testclient import TestClient


def test_pricing_tiers_and_current_subscription(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # 1. Tiers endpoint
    tiers_res = client.get("/api/v1/subscriptions/tiers")
    assert tiers_res.status_code == 200
    tiers_data = tiers_res.json()
    tier_names = [t["tier"] for t in tiers_data["tiers"]]
    assert "FREE" in tier_names
    assert "STARTER" in tier_names
    assert "GROWTH" in tier_names
    assert "PRO" in tier_names
    assert "INSTITUTIONAL" in tier_names
    assert "CUSTOM" in tier_names

    # Check exact prices
    tier_map = {t["tier"]: t for t in tiers_data["tiers"]}
    assert tier_map["FREE"]["price_usd"] == 0.0
    assert tier_map["STARTER"]["price_usd"] == 19.0
    assert tier_map["GROWTH"]["price_usd"] == 49.0
    assert tier_map["PRO"]["price_usd"] == 99.0
    assert tier_map["INSTITUTIONAL"]["price_usd"] == 249.0

    # 2. Current subscription (Defaults to FREE)
    sub_res = client.get("/api/v1/subscriptions/current", headers=headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["tier"] == "FREE"
    assert sub_res.json()["status"] == "ACTIVE"


def test_payment_webhooks_and_subscription_upgrade(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]
    org_id = registered_customer["user"]["organization_id"]

    # 1. Simulate Flutterwave charge.completed webhook
    flw_payload = {
        "event": "charge.completed",
        "data": {
            "id": 987654321,
            "tx_ref": "flw_test_ref_001",
            "amount": 29000.0,
            "currency": "NGN",
            "status": "successful",
            "meta": {"org_id": org_id, "tier": "STARTER"},
        },
    }
    flw_res = client.post(
        "/api/v1/subscriptions/webhook/flutterwave",
        json=flw_payload,
        headers={"verif-hash": "caravan-flw-secret-hash"},
    )
    assert flw_res.status_code == 200
    assert flw_res.json()["payment_status"] == "SUCCESSFUL"
    assert flw_res.json()["tier"] == "STARTER"

    # Verify customer subscription upgraded to STARTER
    sub_res = client.get("/api/v1/subscriptions/current", headers=headers)
    assert sub_res.json()["tier"] == "STARTER"
    assert sub_res.json()["billing_provider"] == "FLUTTERWAVE"

    # 2. Simulate Paystack charge.success webhook
    pstk_payload = {
        "event": "charge.success",
        "data": {
            "reference": "pstk_test_ref_002",
            "amount": 7500000,  # 75,000 NGN in kobo
            "currency": "NGN",
            "status": "success",
            "metadata": {"org_id": org_id, "tier": "GROWTH"},
        },
    }
    pstk_res = client.post(
        "/api/v1/subscriptions/webhook/paystack",
        json=pstk_payload,
        headers={"x-paystack-signature": "caravan-paystack-webhook-secret"},
    )
    assert pstk_res.status_code == 200
    assert pstk_res.json()["payment_status"] == "SUCCESSFUL"
    assert pstk_res.json()["tier"] == "GROWTH"

    # Verify upgraded to GROWTH
    sub_res2 = client.get("/api/v1/subscriptions/current", headers=headers)
    assert sub_res2.json()["tier"] == "GROWTH"
    assert sub_res2.json()["billing_provider"] == "PAYSTACK"

    # 3. Duplicate webhook should be idempotent
    dup_res = client.post("/api/v1/subscriptions/webhook/paystack", json=pstk_payload)
    assert dup_res.status_code == 200
    assert dup_res.json()["status"] == "ALREADY_PROCESSED"

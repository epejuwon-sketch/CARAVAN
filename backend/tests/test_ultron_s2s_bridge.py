"""Test ULTRON Scoped S2S Bridge for CARAVAN Operations."""

from fastapi.testclient import TestClient


def test_ultron_bridge_unauthorized_rejection(client: TestClient):
    # Without header -> 401
    res = client.get("/api/v1/bridge/telemetry")
    assert res.status_code == 401

    # With invalid key -> 401
    res2 = client.get("/api/v1/bridge/telemetry", headers={"X-Ultron-Bridge-Key": "invalid-secret"})
    assert res2.status_code == 401


def test_ultron_bridge_authorized_telemetry(client: TestClient):
    bridge_headers = {"X-Ultron-Bridge-Key": "test-ultron-s2s-bridge-key"}

    # 1. Telemetry query
    res = client.get("/api/v1/bridge/telemetry", headers=bridge_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "CARAVAN Standalone Platform"
    assert data["security_identity"] == "AEGIS"
    assert "customers" in data
    assert "funding_intelligence" in data
    assert data["funding_intelligence"]["total_opportunities"] >= 10
    assert "application_pipeline" in data
    assert "financial_overview" in data
    assert "audit_timeline" in data

    # 2. S2S sweep-expired action
    sweep_res = client.post("/api/v1/bridge/sweep-expired", headers=bridge_headers)
    assert sweep_res.status_code == 200
    assert "swept_count" in sweep_res.json()

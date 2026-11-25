"""Test CARAVAN Multi-Tenant Isolation & Security Boundaries."""

from fastapi.testclient import TestClient


def test_cross_tenant_isolation(client: TestClient, registered_customer: dict):
    headers_a = registered_customer["headers"]

    # Register user B
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user.b@competitor.com",
            "password": "CompetitorPassword2026!",
            "full_name": "Bob Venture",
            "organization_name": "Venture B Ltd",
        },
    )
    assert reg_b.status_code == 201
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # User A creates an application
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]
    app_a = client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={"opportunity_id": opp_id, "notes": "Confidential IP for Org A."},
    ).json()

    app_id_a = app_a["application_id"]

    # User B lists applications -> Should NOT see User A's application
    apps_b = client.get("/api/v1/applications", headers=headers_b).json()["applications"]
    assert all(a["application_id"] != app_id_a for a in apps_b)

    # User B attempts to patch User A's application -> 404 (isolated)
    patch_attempt = client.patch(
        f"/api/v1/applications/{app_id_a}",
        headers=headers_b,
        json={"status": "REJECTED"},
    )
    assert patch_attempt.status_code == 404

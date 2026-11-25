"""CARAVAN Standalone Platform — Admin Operations & Notifications Integration Tests."""

from fastapi.testclient import TestClient
from app.core.security import create_access_token


def test_admin_telemetry_and_rbac(client: TestClient, registered_customer: dict):
    cust_token = registered_customer["token"]
    
    # Customer should be denied access to admin telemetry
    res = client.get("/api/v1/admin/telemetry", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 403

    # Super Admin should be granted access
    admin_token = create_access_token({
        "sub": "usr_platform_admin",
        "org_id": "org_platform_sys",
        "email": "admin@caravan.org",
        "role": "SUPER_ADMIN",
    })
    res2 = client.get("/api/v1/admin/telemetry", headers={"Authorization": f"Bearer {admin_token}"})
    assert res2.status_code == 200
    data = res2.json()
    assert "total_users" in data
    assert "total_opportunities" in data
    assert "pending_review_count" in data


def test_notifications_lifecycle(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # Initial get seeds welcome notifications
    res = client.get("/api/v1/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["unread_count"] >= 1

    first_notif_id = data["notifications"][0]["notification_id"]
    # Mark specific notification as read
    res_read = client.post(f"/api/v1/notifications/{first_notif_id}/read", headers=headers)
    assert res_read.status_code == 200

    # Mark all read
    res_all = client.post("/api/v1/notifications/read-all", headers=headers)
    assert res_all.status_code == 200

    res_after = client.get("/api/v1/notifications", headers=headers)
    assert res_after.json()["unread_count"] == 0


def test_admin_discovery_review_and_role_management(client: TestClient, registered_customer: dict):
    admin_token = create_access_token({
        "sub": "usr_platform_admin",
        "org_id": "org_platform_sys",
        "email": "admin@caravan.org",
        "role": "SUPER_ADMIN",
    })
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Ingest candidate opportunity
    candidate_payload = {
        "title": "Federal Ministry of Communications 3MTT Grant",
        "provider": "Federal Ministry of Communications, Innovation and Digital Economy",
        "official_source_url": "https://bmd.nitda.gov.ng/3mtt",
        "funding_type": "GRANT",
        "amount_display": "₦5,000,000 Innovation Support",
        "geographic_eligibility": "Nigeria",
        "applicant_eligibility": "Tech innovation hubs and Fellows",
        "industry_sector": "Technology",
    }
    ingest_res = client.post("/api/v1/admin/opportunities/ingest", headers=admin_headers, json=candidate_payload)
    assert ingest_res.status_code == 200
    opp_id = ingest_res.json()["opportunity_id"]

    # 2. Get review queue
    queue_res = client.get("/api/v1/admin/opportunities/queue", headers=admin_headers)
    assert queue_res.status_code == 200
    queue = queue_res.json()["queue"]
    assert any(q["opportunity_id"] == opp_id for q in queue)

    # 3. Approve opportunity
    approve_res = client.post(
        f"/api/v1/admin/opportunities/{opp_id}/approve",
        headers=admin_headers,
        json={"notes": "Verified via official NITDA portal."},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "PUBLISHED"

    # 4. Update user role
    target_user_id = registered_customer["user"]["user_id"]
    role_res = client.patch(
        f"/api/v1/admin/users/{target_user_id}/role",
        headers=admin_headers,
        json={"role": "OPPORTUNITY_REVIEWER"},
    )
    assert role_res.status_code == 200
    assert role_res.json()["role"] == "OPPORTUNITY_REVIEWER"

    # 5. Check audit logs
    audit_res = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(l["action"] == "USER_ROLE_CHANGED" for l in logs)

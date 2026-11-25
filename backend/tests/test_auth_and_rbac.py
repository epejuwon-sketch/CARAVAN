"""Test CARAVAN User Registration, Login, Token Decoding & RBAC."""

from fastapi.testclient import TestClient


def test_registration_and_login_flow(client: TestClient):
    email = "nneka.okoli@fintech.ng"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123#",
            "full_name": "Nneka Okoli",
            "organization_name": "KudiScale Microfinance",
            "entity_type": "STARTUP",
            "country": "Nigeria",
            "state_location": "Lagos",
            "sector": "FinTech",
            "stage": "SEED",
        },
    )
    assert reg.status_code == 201
    data = reg.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "CUSTOMER"

    # Duplicate registration should return 409
    dup = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123#",
            "full_name": "Nneka Duplicate",
            "organization_name": "KudiScale Microfinance",
        },
    )
    assert dup.status_code == 409

    # Login with valid credentials
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123#"},
    )
    assert login.status_code == 200
    login_data = login.json()
    assert "access_token" in login_data

    # Test /me endpoint
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login_data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["organization"]["name"] == "KudiScale Microfinance"


def test_invalid_login_rejection(client: TestClient):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@caravan.org", "password": "WrongPassword!"},
    )
    assert res.status_code == 401


def test_admin_route_rbac_protection(client: TestClient):
    from app.core.security import create_access_token

    # 1. Unauthenticated request to admin telemetry -> 401 Unauthorized
    unauth = client.get("/api/v1/admin/telemetry")
    assert unauth.status_code == 401

    # 2. Customer token accessing admin telemetry -> 403 Forbidden
    cust_token = create_access_token({
        "sub": "cust_123",
        "org_id": "org_cust",
        "email": "customer@venture.com",
        "role": "CUSTOMER",
    })
    cust_res = client.get(
        "/api/v1/admin/telemetry",
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert cust_res.status_code == 403
    assert "Permission denied" in cust_res.json()["detail"]

    # 3. Admin token accessing admin telemetry -> 200 OK
    admin_token = create_access_token({
        "sub": "admin_999",
        "org_id": "org_admin",
        "email": "admin@caravan.org",
        "role": "ADMIN",
    })
    admin_res = client.get(
        "/api/v1/admin/telemetry",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    telemetry = admin_res.json()
    assert "total_users" in telemetry
    assert "total_applications" in telemetry
    assert "total_opportunities" in telemetry
    assert isinstance(telemetry["applications"], list)
    assert isinstance(telemetry["users"], list)


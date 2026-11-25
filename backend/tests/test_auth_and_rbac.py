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
    # 1. Unknown email -> 401
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@caravan.org", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

    # Register a user to test bad password
    email = "registered.user@venture.ng"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "CorrectPassword123#",
            "full_name": "Registered User",
            "organization_name": "Venture NG",
        },
    )
    assert reg.status_code == 201

    # 2. Known email with wrong password -> 401
    bad_pass = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert bad_pass.status_code == 401
    assert "Invalid email or password" in bad_pass.json()["detail"]

    # 3. Missing password field -> 422
    missing_pass = client.post(
        "/api/v1/auth/login",
        json={"email": email},
    )
    assert missing_pass.status_code == 422

    # 4. Missing email field -> 422
    missing_email = client.post(
        "/api/v1/auth/login",
        json={"password": "SomePassword123#"},
    )
    assert missing_email.status_code == 422

    # 5. Empty payload -> 422
    empty_body = client.post(
        "/api/v1/auth/login",
        json={},
    )
    assert empty_body.status_code == 422


def test_password_hasher_and_verification_robustness():
    from app.core.security import verify_password, hash_password

    # Normal hashing and verification
    h = hash_password("MySecurePassword123!")
    assert verify_password("MySecurePassword123!", h) is True
    assert verify_password("WrongPassword!", h) is False

    # Robust handling of malformed or invalid hashes (must NOT raise unhandled exception)
    assert verify_password("pass", "") is False
    assert verify_password("pass", None) is False  # type: ignore
    assert verify_password("pass", "plain_text_hash") is False
    assert verify_password("pass", "$2b$12$invalidb2hashpaddingpaddingpadding") is False
    assert verify_password("", h) is False


def test_multi_tenant_isolation_and_organization_context(client: TestClient):
    # Register Tenant A
    res_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@tenant-alpha.com",
            "password": "PasswordAlpha123#",
            "full_name": "Alpha Owner",
            "organization_name": "Alpha Enterprise Ltd",
        },
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    org_a_id = res_a.json()["user"]["organization_id"]

    # Register Tenant B
    res_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@tenant-beta.com",
            "password": "PasswordBeta123#",
            "full_name": "Beta Owner",
            "organization_name": "Beta Innovations Ltd",
        },
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    org_b_id = res_b.json()["user"]["organization_id"]

    # Verify distinct organizations
    assert org_a_id != org_b_id

    # Verify /me endpoint returns respective tenant data
    me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert me_a.status_code == 200
    assert me_a.json()["organization_id"] == org_a_id
    assert me_a.json()["organization"]["name"] == "Alpha Enterprise Ltd"

    me_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert me_b.status_code == 200
    assert me_b.json()["organization_id"] == org_b_id
    assert me_b.json()["organization"]["name"] == "Beta Innovations Ltd"


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


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


def test_production_jwt_secret_configuration_enforcement(monkeypatch):
    import pytest
    from app.core.config import CaravanSettings, get_settings

    # 1. In production, missing or default JWT key must fail safely with an explicit ValueError
    monkeypatch.setenv("CARAVAN_ENV", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError) as excinfo:
        CaravanSettings(CARAVAN_ENV="production", JWT_SECRET_KEY="")
    assert "JWT_SECRET_KEY must be explicitly configured" in str(excinfo.value)
    assert "Automatic ephemeral generation is disabled" in str(excinfo.value)

    # 2. Key shorter than 32 bytes must be rejected
    with pytest.raises(ValueError) as excinfo_short:
        CaravanSettings(CARAVAN_ENV="production", JWT_SECRET_KEY="short-key-less-than-32-bytes")
    assert "at least 32 bytes" in str(excinfo_short.value)

    # 3. Default dev key must be rejected in production
    with pytest.raises(ValueError):
        CaravanSettings(CARAVAN_ENV="production", JWT_SECRET_KEY="caravan-ephemeral-dev-jwt-key-not-for-production")

    # 4. Valid 32+ byte key succeeds in production even with ULTRON_BRIDGE_API_KEY unset (standalone operation)
    valid_key = "a_very_secure_persistent_key_for_production_32bytes"
    prod_settings = CaravanSettings(CARAVAN_ENV="production", JWT_SECRET_KEY=valid_key, ULTRON_BRIDGE_API_KEY="")
    assert prod_settings.JWT_SECRET_KEY == valid_key
    assert prod_settings.ULTRON_BRIDGE_API_KEY == ""

    get_settings.cache_clear()


def test_persistent_jwt_continuity_across_instances_and_restarts(monkeypatch, client: TestClient):
    """Verify separate serverless instances or restarts using the same configured secret validate existing tokens."""
    import secrets
    from app.core.config import get_settings
    from app.core.security import create_access_token, decode_access_token

    persistent_secret = f"prod-secret-{secrets.token_hex(32)}"

    # Instance 1: Generate token
    monkeypatch.setenv("JWT_SECRET_KEY", persistent_secret)
    get_settings.cache_clear()

    token = create_access_token({
        "sub": "usr_serverless_continuity_1",
        "org_id": "org_continuity_1",
        "email": "continuity@caravan.org",
        "role": "CUSTOMER",
    })

    # Simulate Instance 2 (or process restart) with the same configured secret
    get_settings.cache_clear()
    payload = decode_access_token(token)
    assert payload["sub"] == "usr_serverless_continuity_1"
    assert payload["org_id"] == "org_continuity_1"
    assert payload["email"] == "continuity@caravan.org"

    # Verify authenticated request succeeds on the application
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user_id"] == "usr_serverless_continuity_1"


def test_jwt_incorrect_secret_rejection(monkeypatch, client: TestClient):
    """Verify tokens signed with an incorrect or rotated secret are safely rejected."""
    import secrets
    from app.core.config import get_settings
    import jwt

    # Token signed with Secret A
    secret_a = f"secret-a-{secrets.token_hex(32)}"
    token_from_other_secret = jwt.encode(
        {"sub": "usr_hacker", "org_id": "org_hacker", "email": "hacker@evil.com", "role": "CUSTOMER"},
        secret_a,
        algorithm="HS256",
    )

    # Server configured with Secret B
    secret_b = f"secret-b-{secrets.token_hex(32)}"
    monkeypatch.setenv("JWT_SECRET_KEY", secret_b)
    get_settings.cache_clear()

    # Protected endpoint must reject token with 401 Unauthorized
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_from_other_secret}"})
    assert res.status_code == 401
    assert "Invalid or expired authentication token" in res.json()["detail"]


def test_standalone_customer_login_without_ultron_bridge(monkeypatch, client: TestClient):
    """Verify that ULTRON bridge absence does NOT prevent customer registration, login, and operations."""
    monkeypatch.delenv("ULTRON_BRIDGE_API_KEY", raising=False)
    from app.core.config import get_settings
    get_settings.cache_clear()

    email = "independent.founder@nigeria.ng"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "IndependentPass123#",
            "full_name": "Amaka Eze",
            "organization_name": "Independent Agro Ltd",
        },
    )
    assert reg.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "IndependentPass123#"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


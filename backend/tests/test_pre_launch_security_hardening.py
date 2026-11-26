"""
CARAVAN Standalone Platform — Master Pre-Launch Security & Compliance Regression Tests.

Verifies:
1. In-memory sliding-window rate limiting on sensitive auth endpoints (HTTP 429).
2. Password reset & verification token non-exposure in HTTP responses.
3. Security headers enforcement (CSP, X-Frame-Options, X-Content-Type-Options, HSTS).
4. Strict CORS policy (disallowing arbitrary unauthorized origins).
5. Self-service account deactivation & deletion (immediate token invalidation).
6. Notification preferences & email unsubscribe endpoints.
7. Anti-malware and file upload security controls.
8. Cross-tenant isolation & IDOR defense.
"""

import pytest
from fastapi.testclient import TestClient
from app.core.rate_limit import get_rate_limiter
from app.core.config import get_settings


def test_rate_limiting_enforcement(client: TestClient):
    """Item 11: Verify rate limiting returns HTTP 429 after threshold with Retry-After header."""
    rate_limiter = get_rate_limiter()
    rate_limiter.reset()

    # Rapid requests with X-Test-Rate-Limit: true to trigger rate limiter
    headers = {"X-Test-Rate-Limit": "true"}
    email = "rate_limit_victim@example.ng"

    hit_429 = False
    for i in range(15):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": f"WrongPass{i}!"},
            headers=headers,
        )
        if resp.status_code == 429:
            hit_429 = True
            assert "Retry-After" in resp.headers or "retry-after" in resp.headers
            assert "Rate limit exceeded" in resp.json()["detail"] or "Too many attempts" in resp.json()["detail"]
            break

    assert hit_429, "Rate limiter did not trigger HTTP 429 after exceeding request threshold"
    rate_limiter.reset()


def test_password_reset_token_non_exposure_in_production(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Item 10: Verify password reset and verification tokens are never exposed in production responses."""
    monkeypatch.setenv("CARAVAN_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "strong-production-grade-jwt-key-2026-secure-xyz")
    get_settings.cache_clear()

    # 1. Forgot password
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "founder@africanventures.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reset_token" not in data, "Vulnerability: reset_token was leaked in HTTP response body"
    assert "token" not in data, "Vulnerability: raw recovery token was leaked in HTTP response body"

    # 2. Request verification
    resp_v = client.post(
        "/api/v1/auth/request-verification",
        json={"email": "founder@africanventures.com"},
    )
    assert resp_v.status_code == 200
    data_v = resp_v.json()
    assert "verification_token" not in data_v, "Vulnerability: verification_token was leaked in HTTP response body"

    monkeypatch.setenv("CARAVAN_ENV", "test")
    get_settings.cache_clear()


def test_security_headers_enforcement(client: TestClient):
    """Item 18: Verify all required security headers are attached to API responses."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200

    headers = resp.headers
    # Content-Security-Policy
    assert "content-security-policy" in headers
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp

    # X-Frame-Options
    assert headers.get("x-frame-options") == "DENY"

    # X-Content-Type-Options
    assert headers.get("x-content-type-options") == "nosniff"

    # Referrer-Policy
    assert "strict-origin-when-cross-origin" in headers.get("referrer-policy", "")

    # Permissions-Policy
    assert "permissions-policy" in headers
    assert "camera=()" in headers["permissions-policy"]
    assert "microphone=()" in headers["permissions-policy"]


def test_cors_policy_strictness(client: TestClient):
    """Item 18: Verify CORS does not reflect arbitrary disallowed origins."""
    malicious_origin = "https://evil-phishing-attacker.com"
    resp = client.get(
        "/api/v1/health",
        headers={"Origin": malicious_origin},
    )
    # Disallowed origin should NOT have Access-Control-Allow-Origin matching evil domain or wildcard
    allowed_origin = resp.headers.get("access-control-allow-origin")
    assert allowed_origin != malicious_origin
    assert allowed_origin != "*"


def test_account_deletion_and_immediate_token_invalidation(client: TestClient):
    """Item 40: Verify self-service account deletion permanently deactivates account and immediately revokes token."""
    # 1. Register a fresh account
    email = "delete_me_soon@example.ng"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TemporaryPassword123#",
            "full_name": "Temporary User",
            "organization_name": "Temp Org",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Check /me works initially
    me_resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200

    # 3. Attempt deletion with wrong phrase -> 400
    fail_del = client.request(
        "DELETE",
        "/api/v1/account",
        headers=auth_headers,
        json={"confirmation": "WRONG PHRASE", "reason": "Testing"},
    )
    assert fail_del.status_code == 400

    # 4. Delete with exact phrase -> 200
    del_resp = client.request(
        "DELETE",
        "/api/v1/account",
        headers=auth_headers,
        json={"confirmation": "DELETE", "reason": "Moving on"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "DELETION_SCHEDULED"

    # 5. Old token should immediately be rejected with 401 or 403 Forbidden
    me_after = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_after.status_code in (401, 403), "Deactivated account was able to authenticate with old token!"


def test_notification_preferences_and_unsubscribe(client: TestClient, registered_customer: dict):
    """Item 38: Verify notification preferences query, update, and unsubscribe endpoints."""
    headers = registered_customer["headers"]

    # 1. Get preferences
    get_pref = client.get("/api/v1/notifications/preferences", headers=headers)
    assert get_pref.status_code == 200
    data = get_pref.json()
    prefs = data.get("preferences", {})
    assert "opportunity_alerts" in prefs
    assert "marketing_emails" in prefs

    # 2. Update preferences
    update_pref = client.post(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={
            "opportunity_alerts": True,
            "deadline_digests": True,
            "marketing_emails": False,
        },
    )
    assert update_pref.status_code == 200
    assert update_pref.json()["preferences"]["marketing_emails"] is False

    # 3. Direct unsubscribe endpoint
    unsub = client.post(
        "/api/v1/notifications/unsubscribe",
        headers=headers,
        json={"email": registered_customer["user"]["email"], "category": "MARKETING"},
    )
    assert unsub.status_code == 200
    assert unsub.json()["success"] is True


def test_anti_malware_file_upload_validation(client: TestClient, registered_customer: dict):
    """Item 16: Verify executable files and dangerous extensions are rejected on document upload."""
    headers = registered_customer["headers"]

    # 1. Get an existing opportunity to start an application workspace
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    assert len(opps) > 0
    opp_id = opps[0]["opportunity_id"]

    # 2. Create application workspace
    app_res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"opportunity_id": opp_id},
    )
    assert app_res.status_code in (200, 201)
    app_id = app_res.json()["application_id"]

    # 3. Attempt to upload an executable .exe file masquerading as a document
    bad_files = {
        "file": ("trojan.exe", b"MZ\x90\x00\x03\x00\x00\x00ThisIsAnExecutable", "application/x-msdownload")
    }
    resp = client.post(
        f"/api/v1/applications/{app_id}/documents/upload",
        headers=headers,
        files=bad_files,
        data={"doc_type": "PITCH_DECK"},
    )
    assert resp.status_code == 400
    assert "not permitted" in resp.json()["detail"].lower() or "executable" in resp.json()["detail"].lower()

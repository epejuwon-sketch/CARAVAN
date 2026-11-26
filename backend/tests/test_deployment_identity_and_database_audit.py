"""Tests for deployment identity, non-sensitive version endpoint, and database audit probes."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.security import create_access_token
from app.core.config import get_settings

client = TestClient(app)


@pytest.fixture
def admin_headers():
    token = create_access_token({
        "sub": "usr_test_platform_admin",
        "email": "admin@caravan.internal",
        "role": "PLATFORM_ADMIN",
        "org_id": "org_platform_root",
        "token_version": 1,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer_headers():
    token = create_access_token({
        "sub": "usr_test_ordinary_customer",
        "email": "customer@example.com",
        "role": "CUSTOMER",
        "org_id": "org_test_customer",
        "token_version": 1,
    })
    return {"Authorization": f"Bearer {token}"}


def test_version_endpoint_deployment_identity():
    """Verify non-sensitive version and build identity endpoint."""
    res = client.get("/api/v1/version")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "CARAVAN Funding Intelligence Platform"
    assert "build_commit" in data
    # Ensure no credentials, internal deployment targets or asset lists are exposed publicly
    for k in ("password", "secret", "database_url", "token", "frontend_assets", "deployment_target", "vercel_deployment_id"):
        assert k not in data


def test_public_health_minimalism():
    """Verify that public health endpoint returns only minimal status and timestamp."""
    res = client.get("/api/v1/health")
    assert res.status_code in (200, 503)
    data = res.json()
    assert data["service"] == "CARAVAN Funding Intelligence Platform"
    assert "status" in data
    assert "timestamp" in data
    # Ensure no database provider, target host or failure details are exposed
    for k in ("database_provider", "target_host", "failure_category", "storage_mode", "latency_ms"):
        assert k not in data


def test_health_database_audit_endpoint_access_control(admin_headers, customer_headers):
    """Verify database identity and RLS status audit endpoint access control."""
    # 1. Signed-out visitor is rejected with 401
    res_anon = client.get("/api/v1/health/database")
    assert res_anon.status_code == 401

    # 2. Ordinary customer is rejected with 403
    res_cust = client.get("/api/v1/health/database", headers=customer_headers)
    assert res_cust.status_code == 403

    # 3. Platform administrator is authorized
    res_admin = client.get("/api/v1/health/database", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["status"] == "ready"
    assert "database_provider" in data


def test_health_tenant_isolation_audit_access_control(admin_headers, customer_headers):
    """Verify non-destructive tenant isolation probe access control."""
    # 1. Signed-out visitor is rejected with 401
    res_anon = client.get("/api/v1/health/tenant-isolation-audit")
    assert res_anon.status_code == 401

    # 2. Ordinary customer is rejected with 403
    res_cust = client.get("/api/v1/health/tenant-isolation-audit", headers=customer_headers)
    assert res_cust.status_code == 403

    # 3. Platform administrator is authorized
    res_admin = client.get("/api/v1/health/tenant-isolation-audit", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["missing_context_fails_closed"] is True
    assert data["all_14_tables_isolated"] is True
    assert data["tables_isolated_count"] == 14
    assert data["admin_bypass_strictly_blocked"] is True
    assert data["overall_isolation_status"] in ("VERIFIED", "SKIPPED_ON_NON_POSTGRES")


def test_health_rate_limiter_audit_access_control(admin_headers, customer_headers):
    """Verify rate limiter outage verification probe access control."""
    # 1. Signed-out visitor is rejected with 401
    res_anon = client.get("/api/v1/health/rate-limiter-audit")
    assert res_anon.status_code == 401

    # 2. Ordinary customer is rejected with 403
    res_cust = client.get("/api/v1/health/rate-limiter-audit", headers=customer_headers)
    assert res_cust.status_code == 403

    # 3. Platform administrator is authorized
    res_admin = client.get("/api/v1/health/rate-limiter-audit", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["policy"] == "FAIL_CLOSED_ON_AUTHENTICATION"
    assert data["sensitive_outage_status_code"] == 503
    assert data["sensitive_retry_after_header"] == "15"
    assert data["sensitive_fail_closed_verified"] is True
    assert data["non_sensitive_safe_fallback_verified"] is True
    assert data["overall_rate_limiter_status"] == "VERIFIED"

"""Tests for deployment identity, non-sensitive version endpoint, and database audit probes."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.db.session import get_engine

client = TestClient(app)


def test_version_endpoint_deployment_identity():
    """Verify non-sensitive version and build identity endpoint."""
    res = client.get("/api/v1/version")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "CARAVAN Funding Intelligence Platform"
    assert "build_commit" in data
    assert "git_commit" in data
    assert "vercel_deployment_id" in data
    assert "js" in data["frontend_assets"]
    assert "css" in data["frontend_assets"]
    # Ensure no credentials or URLs are exposed
    for k in ("password", "secret", "database_url", "token"):
        assert k not in data


def test_health_database_audit_endpoint():
    """Verify database identity and RLS status audit endpoint."""
    res = client.get("/api/v1/health/database")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "database_provider" in data
    
    # If tested against PostgreSQL, verify detailed audit fields
    if data.get("dialect") != "sqlite":
        assert "caravan_app_role" in data
        assert data["caravan_app_role"]["has_nobypassrls"] is True
        assert data["caravan_app_role"]["can_escalate_to_caravan_admin"] is False
        assert "tenant_tables_rls" in data
        assert data["tenant_tables_rls"]["total_tables_checked"] == 14
        assert data["tenant_tables_rls"]["all_14_tables_enabled_and_forced"] is True
        assert data["policies"]["all_policies_enforce_admin_role_check"] is True


def test_health_tenant_isolation_audit():
    """Verify non-destructive tenant isolation probe against all 14 tables."""
    res = client.get("/api/v1/health/tenant-isolation-audit")
    assert res.status_code == 200
    data = res.json()
    assert data["missing_context_fails_closed"] is True
    assert data["all_14_tables_isolated"] is True
    assert data["tables_isolated_count"] == 14
    assert data["admin_bypass_strictly_blocked"] is True
    assert data["overall_isolation_status"] in ("VERIFIED", "SKIPPED_ON_NON_POSTGRES")


def test_health_rate_limiter_audit():
    """Verify rate limiter fail-closed outage verification probe."""
    res = client.get("/api/v1/health/rate-limiter-audit")
    assert res.status_code == 200
    data = res.json()
    assert data["policy"] == "FAIL_CLOSED_ON_AUTHENTICATION"
    assert data["sensitive_outage_status_code"] == 503
    assert data["sensitive_retry_after_header"] == "15"
    assert data["sensitive_fail_closed_verified"] is True
    assert data["non_sensitive_safe_fallback_verified"] is True
    assert data["overall_rate_limiter_status"] == "VERIFIED"

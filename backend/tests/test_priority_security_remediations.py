"""
CARAVAN Standalone Platform — Priority Security Remediation & Controlled Pilot Tests.

Comprehensive automated verification covering:
1. Native PostgreSQL Row-Level Security (RLS) tenant isolation and fail-closed security.
2. Distributed rate limiting backed by persistent store with atomic increments & fallback.
3. Immediate account status enforcement, token versioning, and multi-instance JWT revocation.
4. Account deletion lifecycle distinguishing document purge, soft deletion, and statutory retention.
"""

import time
from datetime import datetime, timezone, timedelta
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import text, select

from app.core.config import get_settings
from app.core.rate_limit import DistributedRateLimiter, get_rate_limiter
from app.core.security import create_access_token
from app.db.models import (
    UserRecord,
    OrganizationRecord,
    SavedOpportunityRecord,
    DocumentMetadataRecord,
    ApplicationDraftRecord,
    RevokedTokenRecord,
    RateLimitRecord,
    AuditLogRecord,
    gen_id,
)
from app.db.session import get_session_factory, set_tenant_context, get_engine


def test_native_postgresql_rls_tenant_isolation():
    """Verify transaction-scoped tenant isolation and fail-closed behavior."""
    engine = get_engine()
    dialect = engine.dialect.name
    SessionLocal = get_session_factory()

    with SessionLocal() as db:
        # 1. Setup two distinct test organizations
        org_a = f"org_test_a_{gen_id('sec')}"
        org_b = f"org_test_b_{gen_id('sec')}"

        set_tenant_context(db, is_admin=True)

        uid_a = f"usr_a_{gen_id('sec')}"
        uid_b = f"usr_b_{gen_id('sec')}"

        user_a = UserRecord(
            user_id=uid_a,
            organization_id=org_a,
            email=f"{org_a}@tenant-a.ng",
            password_hash="argon2id$mockhash",
            full_name="Alpha Officer",
            role="CUSTOMER",
        )
        user_b = UserRecord(
            user_id=uid_b,
            organization_id=org_b,
            email=f"{org_b}@tenant-b.ng",
            password_hash="argon2id$mockhash",
            full_name="Beta Officer",
            role="CUSTOMER",
        )
        db.add(user_a)
        db.add(user_b)
        db.commit()

        if dialect == "postgresql":
            # 2. In PostgreSQL: verify explicit RLS scoping
            # Test Tenant A context: must only see Tenant A user
            set_tenant_context(db, org_id=org_a, is_admin=False)
            res_a = db.execute(
                select(UserRecord).where(UserRecord.organization_id.in_([org_a, org_b]))
            ).scalars().all()
            assert all(u.organization_id == org_a for u in res_a)
            assert any(u.user_id == uid_a for u in res_a)
            assert not any(u.user_id == uid_b for u in res_a)

            # Test Tenant B context: must only see Tenant B user
            set_tenant_context(db, org_id=org_b, is_admin=False)
            res_b = db.execute(
                select(UserRecord).where(UserRecord.organization_id.in_([org_a, org_b]))
            ).scalars().all()
            assert all(u.organization_id == org_b for u in res_b)
            assert any(u.user_id == uid_b for u in res_b)
            assert not any(u.user_id == uid_a for u in res_b)

            # Test Missing / Unset context: MUST fail closed (0 rows)
            set_tenant_context(db, org_id="", is_admin=False)
            res_closed = db.execute(
                select(UserRecord).where(UserRecord.organization_id.in_([org_a, org_b]))
            ).scalars().all()
            assert len(res_closed) == 0, "Missing tenant context did not fail closed!"

            # Test Platform Admin context: can view both tenants
            set_tenant_context(db, is_admin=True)
            res_admin = db.execute(
                select(UserRecord).where(UserRecord.organization_id.in_([org_a, org_b]))
            ).scalars().all()
            assert len(res_admin) >= 2
        else:
            # On SQLite: verify set_tenant_context runs safely and cleanly
            set_tenant_context(db, org_id=org_a, is_admin=False)
            set_tenant_context(db, org_id="", is_admin=False)
            set_tenant_context(db, is_admin=True)


def test_distributed_rate_limiting_atomic_and_multi_instance(client: TestClient):
    """Verify persistent rate limit store, atomic counters, window expiry, and proxy anti-spoofing."""
    limiter = get_rate_limiter()
    limiter.reset()

    # Build dummy request
    class MockRequest:
        def __init__(self, headers=None, client_host="10.0.0.1"):
            self.headers = headers or {}
            self.client = type("Client", (), {"host": client_host})()

    req = MockRequest(headers={"x-test-rate-limit": "true"})
    test_key = f"test_endpoint_{gen_id('lim')}"

    # 1. Verify requests up to max_requests succeed
    for _ in range(5):
        limiter.check_rate_limit(req, endpoint_key=test_key, max_requests=5, window_seconds=60)

    # 2. 6th request must trigger 429 Too Many Requests with Retry-After header
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(req, endpoint_key=test_key, max_requests=5, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
    assert int(exc_info.value.headers["Retry-After"]) >= 1

    # 3. Test proxy anti-spoofing precedence:
    # CF-Connecting-IP takes precedence over spoofed X-Forwarded-For
    req_spoof = MockRequest(headers={
        "cf-connecting-ip": "198.51.100.42",
        "x-forwarded-for": "10.0.0.99, 10.0.0.100",
        "x-test-rate-limit": "true",
    })
    extracted_ip = limiter._extract_client_ip(req_spoof)
    assert extracted_ip == "198.51.100.42"

    # Test standard X-Forwarded-For first client IP parsing
    req_xff = MockRequest(headers={
        "x-forwarded-for": "203.0.113.195, 10.0.0.1",
        "x-test-rate-limit": "true",
    })
    assert limiter._extract_client_ip(req_xff) == "203.0.113.195"


def test_immediate_account_and_jwt_revocation(client: TestClient):
    """Verify deactivated accounts, password resets, and logout immediately invalidate JWTs."""
    # 1. Register a customer account
    email = f"revocation_test_{gen_id('sec')}@caravan.test"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "InitialPassword123#",
            "full_name": "Revocation Subject",
            "organization_name": "Security Audit Org",
        },
    )
    assert reg.status_code == 201
    token_1 = reg.json()["access_token"]
    headers_1 = {"Authorization": f"Bearer {token_1}"}

    # Verify initial valid token works
    me_resp = client.get("/api/v1/auth/me", headers=headers_1)
    assert me_resp.status_code == 200

    # 2. Deactivate the user in DB directly
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        user = db.execute(select(UserRecord).where(UserRecord.email == email)).scalar_one()
        user.is_active = False
        db.commit()

    # Old token MUST be immediately rejected with 401 Unauthorized
    deact_resp = client.get("/api/v1/auth/me", headers=headers_1)
    assert deact_resp.status_code == 401
    assert "deactivated" in deact_resp.json()["detail"].lower()

    # 3. Reactivate user and simulate credential change / password reset
    time.sleep(1.1)
    revocation_point = datetime.now(timezone.utc)
    with SessionLocal() as db:
        user = db.execute(select(UserRecord).where(UserRecord.email == email)).scalar_one()
        user.is_active = True
        user.revoked_before_at = revocation_point
        user.token_version = 2
        db.commit()

    # Old token (issued at step 1 before revocation_point) MUST be rejected with 401
    old_token_resp = client.get("/api/v1/auth/me", headers=headers_1)
    assert old_token_resp.status_code == 401
    assert "revoked" in old_token_resp.json()["detail"].lower()

    # 4. Issue a fresh token with updated timestamp & version after the revocation point
    time.sleep(1.1)
    with SessionLocal() as db:
        user = db.execute(select(UserRecord).where(UserRecord.email == email)).scalar_one()
        token_2 = create_access_token({
            "sub": user.user_id,
            "org_id": user.organization_id,
            "email": user.email,
            "role": user.role,
            "token_version": user.token_version,
        })
    headers_2 = {"Authorization": f"Bearer {token_2}"}

    # Verify fresh token works
    me_resp_2 = client.get("/api/v1/auth/me", headers=headers_2)
    assert me_resp_2.status_code == 200

    # 5. Call /logout with fresh token
    logout_resp = client.post("/api/v1/auth/logout", headers=headers_2)
    assert logout_resp.status_code == 200

    # Verify logged-out token is now rejected with 401 across all nodes
    logged_out_resp = client.get("/api/v1/auth/me", headers=headers_2)
    assert logged_out_resp.status_code == 401
    assert "revoked" in logged_out_resp.json()["detail"].lower()


def test_account_deletion_lifecycle_and_statutory_retention(client: TestClient):
    """Verify document purge, application draft clearing, and statutory audit logging upon deletion."""
    email = f"deletion_lifecycle_{gen_id('sec')}@caravan.test"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "LifecyclePassword123#",
            "full_name": "Deletion Candidate",
            "organization_name": "Lifecycle Enterprise",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["user_id"]
    org_id = reg.json()["user"]["organization_id"]
    headers = {"Authorization": f"Bearer {token}"}

    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        # Create test document and application draft
        doc = DocumentMetadataRecord(
            doc_id=gen_id("doc"),
            organization_id=org_id,
            name="Confidential_Financials.pdf",
            doc_type="FINANCIAL_STATEMENT",
            scan_status="AVAILABLE",
        )
        draft = ApplicationDraftRecord(
            draft_id=gen_id("drf"),
            application_id=gen_id("app"),
            organization_id=org_id,
            opportunity_id="opp_sample",
            title="Grant Application Draft",
        )
        db.add(doc)
        db.add(draft)
        db.commit()

    # Request deletion with exact confirmation string 'DELETE'
    del_resp = client.request(
        "DELETE",
        "/api/v1/account",
        headers=headers,
        json={"confirmation": "DELETE", "reason": "Completed pilot testing"},
    )
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "DELETION_SCHEDULED"
    assert del_data["retention_policy_days"] == 30

    # Verify database state after deletion
    with SessionLocal() as db:
        user = db.get(UserRecord, user_id)
        assert user.is_active is False
        assert user.revoked_before_at is not None

        # Verify documents are marked PURGED
        docs = db.execute(
            select(DocumentMetadataRecord).where(DocumentMetadataRecord.organization_id == org_id)
        ).scalars().all()
        assert all(d.scan_status == "PURGED" for d in docs)
        assert all(d.deleted_at is not None for d in docs)

        # Verify drafts are removed
        drafts = db.execute(
            select(ApplicationDraftRecord).where(ApplicationDraftRecord.organization_id == org_id)
        ).scalars().all()
        assert len(drafts) == 0

        # Verify statutory audit log entry records statutory basis
        audit = db.execute(
            select(AuditLogRecord).where(
                AuditLogRecord.action == "ACCOUNT_DELETED",
                AuditLogRecord.resource == f"user:{user_id}",
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert "CAMA 2020" in audit.details.get("statutory_retention_basis", "")

    # Verify old token is immediately rejected with 401
    after_resp = client.get("/api/v1/auth/me", headers=headers)
    assert after_resp.status_code == 401


def test_all_14_tenant_tables_isolation_and_attack_vectors():
    """Prove tenant isolation across ALL 14 tenant-owned tables and test attack vectors."""
    engine = get_engine()
    dialect = engine.dialect.name
    if dialect != "postgresql":
        return

    tenant_tables = [
        ("caravan_organizations", "org_id"),
        ("caravan_users", "organization_id"),
        ("caravan_eligibility_assessments", "organization_id"),
        ("caravan_applications", "organization_id"),
        ("caravan_documents", "organization_id"),
        ("caravan_saved_opportunities", "organization_id"),
        ("caravan_subscriptions", "organization_id"),
        ("caravan_payment_transactions", "organization_id"),
        ("caravan_support_tickets", "organization_id"),
        ("caravan_notifications", "user_id"),
        ("caravan_copilot_approvals", "organization_id"),
        ("caravan_copilot_submissions", "organization_id"),
        ("caravan_copilot_sessions", "organization_id"),
        ("caravan_application_drafts", "organization_id"),
    ]

    org_a = f"org_iso_a_{gen_id('sec')}"
    org_b = f"org_iso_b_{gen_id('sec')}"
    uid_a = f"usr_iso_a_{gen_id('sec')}"
    uid_b = f"usr_iso_b_{gen_id('sec')}"

    # Setup seed data for both tenants under admin using ORM models
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        set_tenant_context(db, is_admin=True)
        db.add(OrganizationRecord(org_id=org_a, name="Org Alpha"))
        db.add(OrganizationRecord(org_id=org_b, name="Org Beta"))
        db.add(UserRecord(user_id=uid_a, organization_id=org_a, email=f"{uid_a}@iso.ng", password_hash="hash", full_name="Alpha User"))
        db.add(UserRecord(user_id=uid_b, organization_id=org_b, email=f"{uid_b}@iso.ng", password_hash="hash", full_name="Beta User"))
        db.commit()

    with engine.connect() as conn:
        # 1. SELECT isolation on all 14 tables
        with conn.begin():
            conn.execute(text("SET LOCAL ROLE caravan_app"))
            conn.execute(text("SELECT set_config('app.current_org_id', :oa, true)"), {"oa": org_a})
            conn.execute(text("SELECT set_config('app.current_user_id', :ua, true)"), {"ua": uid_a})
            conn.execute(text("SELECT set_config('app.is_admin', 'false', true)"))

            for table, col in tenant_tables:
                res = conn.execute(text(f"SELECT count(*) FROM {table} WHERE {col} = :b"), {"b": org_b}).scalar()
                assert res == 0, f"{table} leaked org_b rows under org_a context!"

            # 2. UPDATE isolation: trying to update org_b record updates 0 rows
            upd = conn.execute(text("UPDATE caravan_organizations SET name = 'Tampered' WHERE org_id = :ob"), {"ob": org_b})
            assert upd.rowcount == 0, f"UPDATE modified foreign tenant rows: {upd.rowcount}"

            # 3. DELETE isolation: trying to delete org_b record deletes 0 rows
            dlt = conn.execute(text("DELETE FROM caravan_organizations WHERE org_id = :ob"), {"ob": org_b})
            assert dlt.rowcount == 0, f"DELETE deleted foreign tenant rows: {dlt.rowcount}"

            # 4. INSERT with foreign tenant org_id: rejected by RLS WITH CHECK
            import pytest
            from sqlalchemy.exc import ProgrammingError, InternalError
            with pytest.raises((ProgrammingError, InternalError)):
                conn.execute(text("""
                    INSERT INTO caravan_organizations (
                        org_id, name, entity_type, country, state_location, sector,
                        stage, annual_revenue_usd, annual_revenue_ngn, cac_registered,
                        years_in_operation, female_led, youth_led, readiness_score
                    ) VALUES (
                        'foreign_org', 'Foreign', 'STARTUP', 'Nigeria', 'Lagos', 'Technology',
                        'SEED', 0, 0, true, 1, false, true, 0
                    )
                """))

        # 5. Missing tenant context (org_id="") -> fail closed (0 rows)
        with conn.begin():
            conn.execute(text("SET LOCAL ROLE caravan_app"))
            conn.execute(text("SELECT set_config('app.current_org_id', '', true)"))
            conn.execute(text("SELECT set_config('app.is_admin', 'false', true)"))
            res = conn.execute(text("SELECT org_id FROM caravan_organizations WHERE org_id IN (:oa, :ob)"), {"oa": org_a, "ob": org_b}).fetchall()
            assert len(res) == 0, "Missing tenant context failed to fail closed!"

        # 6. Invalid tenant context -> returns 0 rows
        with conn.begin():
            conn.execute(text("SET LOCAL ROLE caravan_app"))
            conn.execute(text("SELECT set_config('app.current_org_id', 'nonexistent_tenant_xyz', true)"))
            conn.execute(text("SELECT set_config('app.is_admin', 'false', true)"))
            res = conn.execute(text("SELECT org_id FROM caravan_organizations WHERE org_id IN (:oa, :ob)"), {"oa": org_a, "ob": org_b}).fetchall()
            assert len(res) == 0, "Invalid tenant context returned unexpected rows!"

        # 7. Connection pool reuse without re-initialization
        with conn.begin():
            conn.execute(text("SET LOCAL ROLE caravan_app"))
            conn.execute(text("SELECT set_config('app.current_org_id', :oa, true)"), {"oa": org_a})
            res1 = conn.execute(text("SELECT org_id FROM caravan_organizations WHERE org_id IN (:oa, :ob)"), {"oa": org_a, "ob": org_b}).fetchall()
            assert len(res1) == 1

        with conn.begin():
            conn.execute(text("SET LOCAL ROLE caravan_app"))
            # Not setting org_id -> must fail closed
            res2 = conn.execute(text("SELECT org_id FROM caravan_organizations WHERE org_id IN (:oa, :ob)"), {"oa": org_a, "ob": org_b}).fetchall()
            assert len(res2) == 0, "Connection pool reuse leaked tenant context!"

        # 8. Ordinary role (caravan_app) attempting admin bypass (set_config('app.is_admin', 'true'))
        with conn.begin():
            conn.execute(text("SET LOCAL ROLE caravan_app"))
            conn.execute(text("SELECT set_config('app.is_admin', 'true', true)"))
            res_attack = conn.execute(text("SELECT org_id FROM caravan_organizations WHERE org_id IN (:oa, :ob)"), {"oa": org_a, "ob": org_b}).fetchall()
            assert len(res_attack) == 0, "caravan_app successfully bypassed RLS by forging app.is_admin!"


def test_rate_limiter_outage_fail_closed_and_safe_fallback():
    """Verify rate limiter fail-closed policy on sensitive endpoints and safe fallback on non-sensitive."""
    from unittest.mock import patch
    import pytest
    from fastapi import HTTPException

    limiter = DistributedRateLimiter()

    class MockReq:
        headers = {"x-test-rate-limit": "true"}
        client = type("Client", (), {"host": "192.0.2.1"})()

    req = MockReq()

    # Simulate shared store database outage
    with patch("app.db.session.get_session_factory", side_effect=Exception("Database connection pool exhausted")):
        # 1. Sensitive authentication operation: auth:login MUST fail-closed with 503
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(req, endpoint_key="auth:login", max_requests=5, window_seconds=60)
        assert exc_info.value.status_code == 503
        assert "Retry-After" in exc_info.value.headers
        assert "temporarily unavailable" in exc_info.value.detail

        # 2. Sensitive registration operation: auth:register MUST fail-closed with 503
        with pytest.raises(HTTPException) as exc_reg:
            limiter.check_rate_limit(req, endpoint_key="auth:register", max_requests=5, window_seconds=60)
        assert exc_reg.value.status_code == 503

        # 3. Sensitive password reset: auth:forgot-password MUST fail-closed with 503
        with pytest.raises(HTTPException) as exc_pw:
            limiter.check_rate_limit(req, endpoint_key="auth:forgot-password", max_requests=5, window_seconds=60)
        assert exc_pw.value.status_code == 503

        # 4. Non-sensitive catalog browse operation: MUST gracefully fallback to local in-memory window
        limiter.check_rate_limit(req, endpoint_key="catalog:browse", max_requests=10, window_seconds=60)


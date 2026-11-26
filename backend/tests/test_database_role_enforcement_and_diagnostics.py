"""CARAVAN Standalone Platform — Database Role Enforcement, Diagnostics & Revocation Tests."""

import os
import time
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select

from app.main import app
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_session_factory, set_tenant_context, get_engine
from app.db.models import UserRecord, OrganizationRecord, RevokedTokenRecord, DocumentMetadataRecord
from app.services.storage_service import get_storage_service

client = TestClient(app)


def test_effective_database_role_lifecycle_on_postgres():
    """TASK 1: Verify the complete database connection lifecycle and role switching.

    Proves that:
    1. Base pool connection user is the pooler user (e.g. postgres / caravan).
    2. Tenant-scoped customer request assumes restricted role caravan_app.
    3. caravan_app has NOBYPASSRLS and NOSUPERUSER.
    4. Transaction rollback/commit reverts current_user and clears app.current_org_id.
    """
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL dialect required for native role switching test.")

    SessionFactory = get_session_factory()

    # 1. Base connection before context
    with SessionFactory() as db:
        base_sess_user = db.execute(text("SELECT session_user")).scalar()
        base_curr_user = db.execute(text("SELECT current_user")).scalar()
        assert base_sess_user is not None
        assert base_curr_user is not None

        # 2. Customer context
        synth_org = "org_synth_test_role_1"
        synth_user = "usr_synth_test_role_1"
        set_tenant_context(db, org_id=synth_org, user_id=synth_user, is_admin=False)

        cust_sess_user = db.execute(text("SELECT session_user")).scalar()
        cust_curr_user = db.execute(text("SELECT current_user")).scalar()
        cust_org = db.execute(text("SELECT current_setting('app.current_org_id', true)")).scalar()
        cust_is_admin = db.execute(text("SELECT current_setting('app.is_admin', true)")).scalar()

        # Session user remains the pool connection identity, while current_user assumes caravan_app
        assert cust_sess_user == base_sess_user
        assert cust_curr_user == "caravan_app"
        assert cust_org == synth_org
        assert cust_is_admin == "false"

        # Verify privileges of effective role caravan_app
        privs = db.execute(text("""
            SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = :rol
        """), {"rol": cust_curr_user}).fetchone()
        assert privs is not None
        assert privs[0] is False, "caravan_app must NOT be a superuser"
        assert privs[1] is False, "caravan_app must have NOBYPASSRLS"

        # 3. Verify rollback reverts current_user and clears context
        db.rollback()
        revert_curr_user = db.execute(text("SELECT current_user")).scalar()
        revert_org = db.execute(text("SELECT current_setting('app.current_org_id', true)")).scalar() or ""
        assert revert_curr_user == base_curr_user
        assert revert_org == ""

    # 4. Connection reuse: next session from pool starts completely clean
    with SessionFactory() as db2:
        clean_curr_user = db2.execute(text("SELECT current_user")).scalar()
        clean_org = db2.execute(text("SELECT current_setting('app.current_org_id', true)")).scalar() or ""
        assert clean_curr_user == base_curr_user
        assert clean_org == ""


def test_admin_database_role_lifecycle_on_postgres():
    """Verify that platform admin operations assume caravan_admin."""
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL dialect required for native role switching test.")

    SessionFactory = get_session_factory()
    with SessionFactory() as db:
        set_tenant_context(db, org_id="org_admin_scope", user_id="usr_admin_scope", is_admin=True)
        admin_curr_user = db.execute(text("SELECT current_user")).scalar()
        admin_is_admin = db.execute(text("SELECT current_setting('app.is_admin', true)")).scalar()

        assert admin_curr_user == "caravan_admin"
        assert admin_is_admin == "true"

        db.rollback()


def test_diagnostic_endpoints_three_persona_access_control():
    """TASK 3: Verify diagnostic endpoints access control across three personas:

    1. Signed-out visitor -> 401 Unauthorized
    2. Ordinary authenticated customer -> 403 Forbidden
    3. Authorized platform administrator -> 200 OK
    """
    admin_token = create_access_token({
        "sub": "usr_audit_platform_admin",
        "email": "platform_admin@caravan.internal",
        "role": "PLATFORM_ADMIN",
        "org_id": "org_platform_root",
        "token_version": 1,
    })
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    customer_token = create_access_token({
        "sub": "usr_audit_regular_customer",
        "email": "customer@example.com",
        "role": "CUSTOMER",
        "org_id": "org_customer_sandbox",
        "token_version": 1,
    })
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    diagnostic_routes = [
        "/api/v1/health/database",
        "/api/v1/health/tenant-isolation-audit",
        "/api/v1/health/rate-limiter-audit",
    ]

    for route in diagnostic_routes:
        # Persona 1: Signed-out visitor
        res_anon = client.get(route)
        assert res_anon.status_code == 401, f"{route} must reject signed-out visitor with 401"
        assert "Authentication required" in res_anon.json()["detail"] or "Invalid" in res_anon.json()["detail"]

        # Persona 2: Ordinary customer
        res_cust = client.get(route, headers=customer_headers)
        assert res_cust.status_code == 403, f"{route} must reject ordinary customer with 403"
        assert "Platform administrator privileges required" in res_cust.json()["detail"]

        # Persona 3: Platform administrator
        res_admin = client.get(route, headers=admin_headers)
        assert res_admin.status_code == 200, f"{route} must authorize platform admin with 200"


def test_jwt_revocation_vector_logout():
    """TASK 4 Vector 1: Logout invalidates active token via JTI blacklist."""
    SessionFactory = get_session_factory()
    test_user_id = "usr_revocation_logout_test"
    test_email = "logout_test@example.com"

    with SessionFactory() as db:
        existing = db.get(UserRecord, test_user_id)
        if not existing:
            user = UserRecord(
                user_id=test_user_id,
                email=test_email,
                full_name="Revocation Tester",
                organization_id="org_revocation_test",
                role="CUSTOMER",
                password_hash=hash_password("Password123!"),
                is_active=True,
                token_version=1,
            )
            db.add(user)
            db.commit()

    token = create_access_token({
        "sub": test_user_id,
        "email": test_email,
        "role": "CUSTOMER",
        "org_id": "org_revocation_test",
        "token_version": 1,
    })
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout
    res_before = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res_before.status_code == 200

    # Call logout
    res_logout = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert res_logout.status_code == 200

    # Verify token is now revoked
    res_after = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res_after.status_code == 401
    assert "revoked" in res_after.json()["detail"].lower()


def test_jwt_revocation_vector_account_deactivation():
    """TASK 4 Vector 2: Account deactivation invalidates existing tokens immediately."""
    SessionFactory = get_session_factory()
    test_user_id = "usr_revocation_deactivate_test"
    test_email = "deactivate_test@example.com"

    with SessionFactory() as db:
        user = db.get(UserRecord, test_user_id)
        if not user:
            user = UserRecord(
                user_id=test_user_id,
                email=test_email,
                full_name="Revocation Tester",
                organization_id="org_revocation_test",
                role="CUSTOMER",
                password_hash=hash_password("Password123!"),
                is_active=True,
                token_version=1,
            )
            db.add(user)
        else:
            user.is_active = True
        db.commit()

    token = create_access_token({
        "sub": test_user_id,
        "email": test_email,
        "role": "CUSTOMER",
        "org_id": "org_revocation_test",
        "token_version": 1,
    })
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Verify token works when user is active
    res_before = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res_before.status_code == 200

    # Deactivate account in database
    with SessionFactory() as db:
        u = db.get(UserRecord, test_user_id)
        u.is_active = False
        db.commit()

    # Verify existing token is immediately rejected
    res_after = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res_after.status_code == 401
    assert "deactivated" in res_after.json()["detail"].lower()


def test_jwt_revocation_vector_password_reset():
    """TASK 4 Vector 3: Password reset invalidates existing tokens via token_version and timestamp."""
    SessionFactory = get_session_factory()
    test_user_id = "usr_revocation_pwreset_test"
    test_email = "pwreset_test@example.com"

    with SessionFactory() as db:
        user = db.get(UserRecord, test_user_id)
        if not user:
            user = UserRecord(
                user_id=test_user_id,
                email=test_email,
                full_name="Revocation Tester",
                organization_id="org_revocation_test",
                role="CUSTOMER",
                password_hash=hash_password("OldPassword123!"),
                is_active=True,
                token_version=1,
                revoked_before_at=datetime.now(timezone.utc),
            )
            db.add(user)
        else:
            user.is_active = True
            user.token_version = 1
        db.commit()

    # Issue token under version 1
    token_v1 = create_access_token({
        "sub": test_user_id,
        "email": test_email,
        "role": "CUSTOMER",
        "org_id": "org_revocation_test",
        "token_version": 1,
    })
    headers_v1 = {"Authorization": f"Bearer {token_v1}"}

    res_before = client.get("/api/v1/auth/me", headers=headers_v1)
    assert res_before.status_code == 200

    # Execute password reset: increment token_version and update revoked_before_at
    reset_token = create_access_token(
        {"sub": test_user_id, "email": test_email, "purpose": "password_reset"},
        expires_delta=timedelta(minutes=15),
    )
    res_reset = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewStrongPassword456!",
    })
    assert res_reset.status_code == 200

    # Old token under version 1 must now be rejected
    res_after = client.get("/api/v1/auth/me", headers=headers_v1)
    assert res_after.status_code == 401
    assert "superseded" in res_after.json()["detail"].lower() or "revoked" in res_after.json()["detail"].lower()


def test_document_deletion_physical_erasure():
    """TASK 4: Verify that document deletion performs physical erasure (shredding),

    not merely updating database status to PURGED.
    """
    storage = get_storage_service()
    org_id = "org_doc_shred_test"
    doc_id = "doc_shred_probe_1"
    sample_content = b"CRITICAL_PROPRIETARY_BUSINESS_PLAN_2026_CONFIDENTIAL"

    # Store document physically
    storage_res = storage.store_document(org_id, doc_id, sample_content)
    file_path = storage._get_org_doc_dir(org_id, quarantined=False) / f"{doc_id}.bin"
    assert file_path.exists(), "Document must exist in physical storage before deletion"

    # Execute storage deletion
    deleted = storage.delete_document(org_id, doc_id)
    assert deleted is True

    # Physical file must no longer exist on disk
    assert not file_path.exists(), "Physical file must be completely unlinked from storage"

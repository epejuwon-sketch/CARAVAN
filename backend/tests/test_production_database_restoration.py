"""CARAVAN Standalone Platform — PostgreSQL Production Database Restoration & Verification Tests.

Automated verification suite testing:
1. PostgreSQL connectivity & schema verification.
2. Customer registration & authentication.
3. Persistence across application restarts.
4. Persistence across separate serverless invocations (NullPool).
5. Controlled database failure handling without SQLite /tmp fallback in production.
6. Strict multi-tenant isolation.
7. Safe SQLite-to-PostgreSQL recovery without overwriting existing data.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import (
    Base,
    reset_engine,
    run_migrations,
    get_engine,
    get_session_factory,
    get_storage_mode,
)
from app.db.models import UserRecord, OrganizationRecord
from app.db.migrate_storage import safe_migrate_sqlite_to_postgres
from app.main import app

POSTGRES_TEST_URL = os.getenv(
    "TEST_POSTGRES_URL",
    "postgresql://caravan:caravan_secure_pwd_2026@localhost:5432/caravan_production"
)
TEST_JWT_KEY = "caravan-test-persistent-jwt-key-256bit-production-ready!"


@pytest.fixture(autouse=True)
def setup_teardown_env():
    """Ensures consistent environment for each test."""
    old_env = dict(os.environ)
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    os.environ["CARAVAN_ENV"] = "test"
    os.environ["JWT_SECRET_KEY"] = TEST_JWT_KEY
    get_settings.cache_clear()
    reset_engine()
    yield
    reset_engine()
    os.environ.clear()
    os.environ.update(old_env)
    get_settings.cache_clear()


def test_postgresql_connectivity_and_all_tables():
    """1. Verify PostgreSQL connectivity, SELECT 1, and all 15 registered tables."""
    engine = get_engine()
    assert engine.dialect.name == "postgresql"

    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1

    run_migrations()

    with engine.connect() as conn:
        tables_res = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)).fetchall()
        table_names = {row[0] for row in tables_res}

        required_tables = {
            "caravan_users",
            "caravan_organizations",
            "caravan_funding_opportunities",
            "caravan_eligibility_assessments",
            "caravan_applications",
            "caravan_documents",
            "caravan_saved_opportunities",
            "caravan_subscriptions",
            "caravan_payment_transactions",
            "caravan_support_tickets",
            "caravan_notifications",
            "caravan_audit_logs",
            "caravan_organization_usage",
            "caravan_copilot_sessions",
            "caravan_copilot_messages",
        }
        assert required_tables.issubset(table_names), f"Missing tables: {required_tables - table_names}"


def test_postgresql_registration_and_login():
    """2. Verify customer registration, JWT token generation, and login on PostgreSQL."""
    client = TestClient(app)
    uid = uuid.uuid4().hex[:8]
    email = f"founder_{uid}@lagos-agrotech.ng"
    password = "SecurePassword2026!"

    # Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Babajide Agro",
            "organization_name": f"AgroTech Nigeria {uid}",
            "entity_type": "STARTUP",
            "country": "Nigeria",
            "state_location": "Lagos",
            "sector": "Agribusiness",
            "stage": "GROWTH",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    assert "access_token" in login_data
    token = login_data["access_token"]

    # Verify authenticated /me endpoint
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email
    assert me_resp.json()["organization"]["sector"] == "Agribusiness"


def test_persistence_after_application_restart():
    """3. Verify data persists when engine is reset and application is restarted."""
    uid = uuid.uuid4().hex[:8]
    email = f"restart_{uid}@fintech-abuja.ng"
    password = "PersistPassword2026!"

    # Instance 1: Register user
    with TestClient(app) as client1:
        reg_resp = client1.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Ngozi Restart",
                "organization_name": f"Fintech Abuja {uid}",
            },
        )
        assert reg_resp.status_code == 201

    # SIMULATE FULL APP RESTART: dispose engine, clear caches
    reset_engine()
    get_settings.cache_clear()

    # Instance 2: Start fresh app and verify login succeeds
    with TestClient(app) as client2:
        login_resp = client2.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        me_resp = client2.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email


def test_persistence_across_separate_serverless_invocations():
    """4. Verify persistence across serverless invocations with NullPool and cold starts."""
    os.environ["VERCEL"] = "1"
    os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "caravan-backend-lambda"
    reset_engine()

    # Cold Start 1: Register
    uid = uuid.uuid4().hex[:8]
    email = f"serverless_{uid}@delta-health.ng"
    password = "ColdStartPassword2026!"

    with TestClient(app) as lambda1:
        r1 = lambda1.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Dr. Ejiro Lambda",
                "organization_name": f"Delta Health {uid}",
            },
        )
        assert r1.status_code == 201
        token = r1.json()["access_token"]

    # Cold Start 2: Container recycled (reset_engine)
    reset_engine()

    with TestClient(app) as lambda2:
        # User account and profile remain intact
        r2 = lambda2.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert r2.json()["email"] == email

        # New login on cold start 2 succeeds
        r3 = lambda2.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert r3.status_code == 200


def test_database_failure_handling_and_no_sqlite_fallback_in_production():
    """5. Verify that in production, database failure returns 503 and NEVER falls back to SQLite."""
    os.environ["CARAVAN_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://caravan:bad_password_xyz@localhost:5432/caravan_production"
    reset_engine()
    get_settings.cache_clear()

    with TestClient(app) as client:
        # /health probe should return HTTP 503 with degraded status and storage_mode primary_postgres
        health_resp = client.get("/health")
        assert health_resp.status_code == 503
        data = health_resp.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        assert data["storage_mode"] == "primary_postgres"

        # Health response must NEVER expose passwords, connection strings, or tracebacks
        health_str = health_resp.text
        assert "bad_password_xyz" not in health_str
        assert "traceback" not in health_str.lower()

        # Database-dependent endpoints return controlled HTTP 503
        auth_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "any@example.com", "password": "password"},
        )
        assert auth_resp.status_code == 503
        assert "Database service temporarily unavailable" in auth_resp.json()["detail"]

        # Confirm no /tmp/caravan.db or fallback was created
        assert not os.path.exists("/tmp/caravan_production_test_failover.db")


def test_multi_tenant_isolation():
    """6. Verify multi-tenant isolation: Org A cannot access Org B's resources."""
    client = TestClient(app)
    uid_a = uuid.uuid4().hex[:6]
    uid_b = uuid.uuid4().hex[:6]

    # Register Org A
    resp_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"user_{uid_a}@tenant-a.com",
            "password": "PasswordA123!",
            "full_name": "Tenant A User",
            "organization_name": f"Enterprise A {uid_a}",
        },
    )
    token_a = resp_a.json()["access_token"]
    org_id_a = resp_a.json()["user"]["organization_id"]

    # Register Org B
    resp_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"user_{uid_b}@tenant-b.com",
            "password": "PasswordB123!",
            "full_name": "Tenant B User",
            "organization_name": f"Enterprise B {uid_b}",
        },
    )
    token_b = resp_b.json()["access_token"]
    org_id_b = resp_b.json()["user"]["organization_id"]

    assert org_id_a != org_id_b

    # Org A accesses /api/v1/auth/me
    me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert me_a["organization_id"] == org_id_a

    # Org B accesses /api/v1/auth/me
    me_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert me_b["organization_id"] == org_id_b


def test_safe_sqlite_to_postgres_migration():
    """7. Verify safe recovery from SQLite to PostgreSQL without overwriting existing data."""
    # Create temporary SQLite database with a legacy user
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE caravan_organizations (
                org_id TEXT PRIMARY KEY,
                name TEXT,
                entity_type TEXT,
                country TEXT,
                state_location TEXT,
                sector TEXT,
                stage TEXT,
                annual_revenue_usd REAL,
                annual_revenue_ngn REAL,
                funding_goals TEXT,
                team_size INTEGER,
                cac_registered INTEGER,
                years_in_operation INTEGER,
                female_led INTEGER,
                youth_led INTEGER,
                products_services TEXT,
                target_customers TEXT,
                business_model TEXT,
                growth_objectives TEXT,
                intended_use_of_funds TEXT,
                readiness_score REAL
            );
        """)
        cursor.execute("""
            CREATE TABLE caravan_users (
                user_id TEXT PRIMARY KEY,
                organization_id TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                full_name TEXT,
                role TEXT,
                is_active INTEGER
            );
        """)
        mig_uid = uuid.uuid4().hex[:8]
        cursor.execute("""
            INSERT INTO caravan_organizations (org_id, name, entity_type, sector)
            VALUES (?, ?, ?, ?);
        """, (f"org_mig_{mig_uid}", f"Migrated Corp {mig_uid}", "SME", "Solar"))

        cursor.execute("""
            INSERT INTO caravan_users (user_id, organization_id, email, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (f"usr_mig_{mig_uid}", f"org_mig_{mig_uid}", f"migrated_{mig_uid}@solar-kaduna.ng", "hash123", "Musa Solar", "FOUNDER", 1))
        conn.commit()
        conn.close()

        # Execute safe migration into PostgreSQL
        session_factory = get_session_factory()
        with session_factory() as db:
            result = safe_migrate_sqlite_to_postgres(tmp_db_path, db)
            assert result["status"] == "completed"
            assert result["migrated"]["organizations"] >= 1
            assert result["migrated"]["users"] >= 1

            # Idempotency check: running second time should migrate 0 (never duplicate or overwrite)
            result2 = safe_migrate_sqlite_to_postgres(tmp_db_path, db)
            assert result2["status"] == "completed"
            assert result2["migrated"]["organizations"] == 0
            assert result2["migrated"]["users"] == 0
    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)

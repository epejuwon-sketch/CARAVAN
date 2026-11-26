"""CARAVAN Standalone Platform — Database Session & PostgreSQL Connection Engine."""

from __future__ import annotations

import logging
import os
import urllib.parse
from pathlib import Path
from typing import Generator, List
from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import get_settings

logger = logging.getLogger("caravan")

Base = declarative_base()

_engine = None
_SessionLocal = None
_migrations_applied = False
_sqlite_migrated = False


def reset_engine():
    """Resets the active database engine and session factory (used in tests and restarts)."""
    global _engine, _SessionLocal, _migrations_applied, _sqlite_migrated
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = None
    _SessionLocal = None
    _migrations_applied = False
    _sqlite_migrated = False


def is_using_fallback() -> bool:
    """Returns False — SQLite /tmp fallback is disabled in CARAVAN production."""
    return False


def get_storage_mode() -> str:
    """Returns the active storage mode."""
    settings = get_settings()
    raw = (settings.DATABASE_URL or "").strip()
    if raw.startswith("sqlite"):
        return "sqlite_development"
    return "primary_postgres"


def normalize_database_url(raw_url: str) -> str:
    """Normalizes database URLs, translates direct IPv6 Supabase hosts to IPv4 poolers, and quotes credentials."""
    settings = get_settings()
    is_prod = settings.CARAVAN_ENV == "production"

    cleaned = raw_url.strip() if raw_url else ""

    # In production, SQLite is strictly forbidden
    if not cleaned or cleaned.startswith("sqlite"):
        if is_prod:
            raise ValueError(
                "Production database configuration error: DATABASE_URL must be configured with a valid "
                "persistent PostgreSQL connection string. Ephemeral SQLite storage is strictly disallowed."
            )
        if not cleaned:
            cleaned = "sqlite:///./caravan.db"
        if cleaned.startswith("sqlite:///./") or cleaned == "sqlite:///caravan.db":
            backend_dir = Path(__file__).resolve().parents[2]
            backend_db = backend_dir / "caravan.db"
            return f"sqlite:///{backend_db}"
        return cleaned

    # Safely handle passwords containing unencoded special characters (e.g. '@', '#')
    candidate = cleaned
    if "://" in candidate:
        scheme, rest = candidate.split("://", 1)
        if "@" in rest:
            auth_part, host_part = rest.rsplit("@", 1)
            if ":" in auth_part:
                user, pwd = auth_part.split(":", 1)
                unquoted_pwd = urllib.parse.unquote(pwd)
                quoted_pwd = urllib.parse.quote(unquoted_pwd, safe="")
                rest = f"{user}:{quoted_pwd}@{host_part}"
        candidate = f"{scheme}://{rest}"

    if candidate.startswith("postgres://"):
        candidate = "postgresql+psycopg://" + candidate[len("postgres://"):]
    elif candidate.startswith("postgresql://"):
        candidate = "postgresql+psycopg://" + candidate[len("postgresql://"):]
    elif candidate.startswith("postgresql+psycopg2://"):
        candidate = "postgresql+psycopg://" + candidate[len("postgresql+psycopg2://"):]

    from sqlalchemy.engine import make_url
    try:
        parsed = make_url(candidate)

        # In serverless/IPv4 environments, convert direct Supabase hosts (db.<ref>.supabase.co)
        # to the IPv4-routable connection pooler
        if parsed.host and parsed.host.startswith("db.") and parsed.host.endswith(".supabase.co"):
            ref = parsed.host[3:-len(".supabase.co")]
            current_user = parsed.username or "postgres"
            if not current_user.endswith(f".{ref}"):
                current_user = f"postgres.{ref}"
            parsed = parsed.set(
                host="aws-1-eu-west-1.pooler.supabase.com",
                port=6543,
                username=current_user,
            )
        elif parsed.host and "pooler.supabase.com" in parsed.host:
            if parsed.username and "." not in parsed.username:
                parsed = parsed.set(username=f"{parsed.username}.pceyszeflfwntralsrmj")

        if parsed.query:
            NON_LIBPQ = {
                "pgbouncer",
                "connection_limit",
                "pool_timeout",
                "schema",
                "supa",
                "prisma",
                "statement_cache_size",
            }
            filtered = {k: v for k, v in parsed.query.items() if k.lower() not in NON_LIBPQ}
            if "sslmode" not in filtered and parsed.host and parsed.host not in ("localhost", "127.0.0.1"):
                filtered["sslmode"] = "require"
            parsed = parsed.set(query=filtered)
        elif parsed.host and parsed.host not in ("localhost", "127.0.0.1"):
            parsed = parsed.set(query={"sslmode": "require"})
        return parsed.render_as_string(hide_password=False)
    except Exception:
        return candidate


def _try_alternate_pooler_candidates(db_url: str) -> List[str]:
    """Generates candidate alternate pooler URLs for Supabase (toggling 6543/5432 and aws-1/aws-0)."""
    candidates = []
    from sqlalchemy.engine import make_url
    try:
        parsed = make_url(db_url)
        if parsed.host and "pooler.supabase.com" in parsed.host:
            current_port = parsed.port or 5432
            alt_port = 6543 if current_port == 5432 else 5432
            candidates.append(parsed.set(port=alt_port).render_as_string(hide_password=False))

            if "aws-1-" in parsed.host:
                alt_host = parsed.host.replace("aws-1-", "aws-0-")
                candidates.append(parsed.set(host=alt_host, port=alt_port).render_as_string(hide_password=False))
                candidates.append(parsed.set(host=alt_host, port=current_port).render_as_string(hide_password=False))
            elif "aws-0-" in parsed.host:
                alt_host = parsed.host.replace("aws-0-", "aws-1-")
                candidates.append(parsed.set(host=alt_host, port=alt_port).render_as_string(hide_password=False))
                candidates.append(parsed.set(host=alt_host, port=current_port).render_as_string(hide_password=False))
    except Exception:
        pass
    return candidates


def get_engine():
    """Initializes and returns the persistent SQLAlchemy engine.

    Never falls back to SQLite in production.
    """
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    db_url = normalize_database_url(settings.DATABASE_URL)
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    if not db_url.startswith("sqlite"):
        engine_kwargs = {"future": True}
        # prepare_threshold=None disables server-side prepared statements for PgBouncer/Supabase transaction poolers
        connect_args = {"connect_timeout": 3, "prepare_threshold": None}
        if is_serverless:
            from sqlalchemy.pool import NullPool
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_pre_ping"] = True
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10

        try:
            candidate_engine = create_engine(
                db_url,
                connect_args=connect_args,
                **engine_kwargs,
            )
            with candidate_engine.connect() as test_conn:
                test_conn.execute(text("SELECT 1"))
            _engine = candidate_engine
            logger.info("Connected successfully to primary PostgreSQL database.")
            return _engine
        except Exception as primary_exc:
            logger.warning("Primary database connection attempt failed: %s", type(primary_exc).__name__)

            # Try alternate pooler candidates (ports 6543/5432 and regions aws-1/aws-0)
            alt_candidates = _try_alternate_pooler_candidates(db_url)
            for alt_url in alt_candidates:
                try:
                    alt_engine = create_engine(
                        alt_url,
                        connect_args=connect_args,
                        **engine_kwargs,
                    )
                    with alt_engine.connect() as alt_conn:
                        alt_conn.execute(text("SELECT 1"))
                    _engine = alt_engine
                    logger.info("Connected successfully to primary PostgreSQL via alternate pooler candidate.")
                    return _engine
                except Exception as alt_exc:
                    logger.warning("Alternate pooler attempt failed: %s", type(alt_exc).__name__)

            # In production, NO fallback to SQLite is permitted
            _engine = None
            raise primary_exc
    else:
        # SQLite is only allowed in development or testing
        connect_args = {"check_same_thread": False, "timeout": 15}
        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            future=True,
        )
        return _engine


def get_session_factory():
    """Returns the thread-safe session factory, executing migrations and data verification."""
    global _SessionLocal, _migrations_applied, _sqlite_migrated
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
        if not _migrations_applied:
            run_migrations()
        if not _sqlite_migrated and engine.dialect.name == "postgresql":
            # Safely migrate any legitimate existing records from local SQLite if present
            try:
                from app.db.migrate_storage import safe_migrate_sqlite_to_postgres
                for candidate_path in ["/tmp/caravan.db", "caravan.db"]:
                    p = Path(candidate_path)
                    if p.exists() and p.stat().st_size > 0:
                        with _SessionLocal() as mig_db:
                            safe_migrate_sqlite_to_postgres(p, mig_db)
                _sqlite_migrated = True
            except Exception as mig_err:
                logger.warning("Local SQLite record recovery notice: %s", mig_err)

    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session.

    Returns a controlled HTTP 503 response if PostgreSQL is unavailable.
    """
    try:
        SessionLocal = get_session_factory()
        db = SessionLocal()
    except Exception as conn_err:
        logger.error("Database connection unavailable in get_db: %s", type(conn_err).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please retry shortly.",
        )

    try:
        yield db
    except (OperationalError, DisconnectionError) as op_err:
        db.rollback()
        logger.error("Database operational error during transaction: %s", type(op_err).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please retry shortly.",
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def set_tenant_context(
    db: Session,
    org_id: str | None = None,
    user_id: str | None = None,
    is_admin: bool = False,
) -> None:
    """Sets transaction-local configuration parameters in PostgreSQL for Row-Level Security.

    Uses is_local=True and SET LOCAL ROLE so the context is strictly bound to the active transaction and
    automatically reverts on COMMIT or ROLLBACK, preventing leakage across pooled connections.
    Safely no-ops on SQLite / non-PostgreSQL dialects.
    """
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            safe_org = (org_id or "").strip()
            safe_user = (user_id or "").strip()
            admin_val = "true" if is_admin else "false"

            if not is_admin:
                try:
                    db.execute(text("SET LOCAL ROLE caravan_app"))
                except Exception:
                    pass
                db.execute(
                    text("SELECT set_config('app.is_admin', 'false', true)"),
                )
            else:
                try:
                    db.execute(text("SET LOCAL ROLE caravan_admin"))
                except Exception:
                    try:
                        db.execute(text("SET LOCAL ROLE NONE"))
                    except Exception:
                        pass
                db.execute(
                    text("SELECT set_config('app.is_admin', 'true', true)"),
                )

            db.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": safe_org},
            )
            db.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": safe_user},
            )
    except Exception as exc:
        logger.debug("set_tenant_context non-blocking notice: %s", exc)


def _execute_migrations():
    """Initializes tables and executes idempotent schema migrations."""
    engine = get_engine()
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    dialect_name = engine.dialect.name
    if dialect_name == "postgresql":
        migration_statements = [
            # caravan_funding_opportunities
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS source_retrieval_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS verification_method VARCHAR(64) DEFAULT 'MANUAL_REGISTRY_AUDIT'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS verification_evidence JSON DEFAULT '{}'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 1.0",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS evidence_completeness VARCHAR(32) DEFAULT 'COMPLETE'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS next_verification_at TIMESTAMPTZ",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS verification_history JSON DEFAULT '[]'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS publication_status VARCHAR(32) DEFAULT 'PUBLISHED'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS official_application_url VARCHAR(500)",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS supporting_source_urls JSON DEFAULT '[]'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS eligible_applicant_types JSON DEFAULT '[]'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS eligible_countries JSON DEFAULT '[]'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS eligible_states JSON DEFAULT '[]'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS eligible_sectors JSON DEFAULT '[]'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS funding_structure VARCHAR(120) DEFAULT 'DIRECT_DISBURSEMENT'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS business_stage VARCHAR(120) DEFAULT 'ALL_STAGES'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS age_restrictions VARCHAR(120) DEFAULT 'NO_RESTRICTION'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS registration_required BOOLEAN DEFAULT TRUE",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS application_method VARCHAR(120) DEFAULT 'ONLINE_PORTAL'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS opportunity_status VARCHAR(64) DEFAULT 'OPEN'",
            "ALTER TABLE caravan_funding_opportunities ADD COLUMN IF NOT EXISTS important_conditions TEXT DEFAULT ''",
            # caravan_organizations
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS annual_revenue_ngn FLOAT DEFAULT 0.0",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS cac_registered BOOLEAN DEFAULT TRUE",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS years_in_operation INTEGER DEFAULT 1",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS female_led BOOLEAN DEFAULT FALSE",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS youth_led BOOLEAN DEFAULT TRUE",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS products_services TEXT DEFAULT ''",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS target_customers VARCHAR(255) DEFAULT ''",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS business_model VARCHAR(120) DEFAULT 'B2B'",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS growth_objectives TEXT DEFAULT ''",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS intended_use_of_funds TEXT DEFAULT ''",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS previous_funding_history JSON DEFAULT '[]'",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS readiness_score FLOAT DEFAULT 0.0",
            "ALTER TABLE caravan_organizations ADD COLUMN IF NOT EXISTS readiness_breakdown JSON DEFAULT '{}'",
            # caravan_documents
            "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS storage_path VARCHAR(512)",
            "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS content_type VARCHAR(128) DEFAULT 'application/octet-stream'",
            "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS scan_status VARCHAR(32) DEFAULT 'AVAILABLE'",
            "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS scan_details JSON DEFAULT '{}'",
            "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS sha256_hash VARCHAR(64)",
            "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
            # copilot tables (idempotent creation)
            """CREATE TABLE IF NOT EXISTS caravan_copilot_approvals (
                approval_id VARCHAR(64) PRIMARY KEY,
                organization_id VARCHAR(64) NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                target_type VARCHAR(64) NOT NULL,
                target_id VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
                approval_type VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER_APPROVAL',
                authorizer_role VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
                authorizer_user_id VARCHAR(64),
                override_reason TEXT NOT NULL DEFAULT '',
                remaining_gaps JSON NOT NULL DEFAULT '[]',
                customer_notes TEXT NOT NULL DEFAULT '',
                approval_hash VARCHAR(64),
                approved_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS caravan_copilot_submissions (
                submission_id VARCHAR(64) PRIMARY KEY,
                application_id VARCHAR(64) NOT NULL,
                organization_id VARCHAR(64) NOT NULL,
                opportunity_id VARCHAR(64) NOT NULL,
                approval_id VARCHAR(64) NOT NULL,
                submission_channel VARCHAR(64) NOT NULL DEFAULT 'OFFICIAL_PORTAL',
                submission_reference VARCHAR(128) NOT NULL,
                confirmation_status VARCHAR(64) NOT NULL DEFAULT 'PACKAGE_PREPARED',
                confirmation_details JSON NOT NULL DEFAULT '{}',
                official_portal_url VARCHAR(500),
                guided_manual_steps JSON NOT NULL DEFAULT '[]',
                payload_snapshot JSON NOT NULL DEFAULT '{}',
                submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            "ALTER TABLE caravan_copilot_submissions ADD COLUMN IF NOT EXISTS confirmation_details JSON DEFAULT '{}'",
            "ALTER TABLE caravan_copilot_submissions ADD COLUMN IF NOT EXISTS official_portal_url VARCHAR(500)",
            "ALTER TABLE caravan_copilot_submissions ADD COLUMN IF NOT EXISTS guided_manual_steps JSON DEFAULT '[]'",
            "ALTER TABLE caravan_copilot_submissions ADD COLUMN IF NOT EXISTS payload_snapshot JSON DEFAULT '{}'",
            """CREATE TABLE IF NOT EXISTS caravan_copilot_sessions (
                session_id VARCHAR(64) PRIMARY KEY,
                organization_id VARCHAR(64) NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
                context_mode VARCHAR(64) NOT NULL DEFAULT 'GENERAL',
                active_opportunity_id VARCHAR(64),
                active_application_id VARCHAR(64),
                is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS caravan_copilot_messages (
                message_id VARCHAR(64) PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL,
                sender VARCHAR(32) NOT NULL,
                content TEXT NOT NULL,
                citations JSON NOT NULL DEFAULT '[]',
                actions JSON NOT NULL DEFAULT '[]',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS caravan_application_drafts (
                draft_id VARCHAR(64) PRIMARY KEY,
                application_id VARCHAR(64) NOT NULL,
                organization_id VARCHAR(64) NOT NULL,
                opportunity_id VARCHAR(64) NOT NULL,
                title VARCHAR(255) NOT NULL,
                executive_summary TEXT NOT NULL DEFAULT '',
                problem_statement TEXT NOT NULL DEFAULT '',
                solution_narrative TEXT NOT NULL DEFAULT '',
                budget_breakdown JSON NOT NULL DEFAULT '[]',
                sections JSON NOT NULL DEFAULT '[]',
                validation_status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
                validation_notes JSON NOT NULL DEFAULT '[]',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
        ]
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for stmt in migration_statements:
                try:
                    conn.execute(text(stmt))
                except Exception as stmt_err:
                    logger.debug("Non-blocking PostgreSQL migration notice: %s", stmt_err)

            # Idempotently execute 002 native PostgreSQL RLS and token revocation migration
            try:
                candidates = [
                    Path(__file__).resolve().parents[2] / "migrations" / "002_native_postgresql_rls_and_revocation.sql",
                    Path(__file__).resolve().parents[1] / "migrations" / "002_native_postgresql_rls_and_revocation.sql",
                    Path("migrations/002_native_postgresql_rls_and_revocation.sql"),
                    Path("backend/migrations/002_native_postgresql_rls_and_revocation.sql"),
                    Path("api/migrations/002_native_postgresql_rls_and_revocation.sql"),
                ]
                for mig_path in candidates:
                    if mig_path.exists():
                        sql_content = mig_path.read_text(encoding="utf-8")
                        conn.execute(text(sql_content))
                        break
            except Exception as rls_err:
                logger.warning("002 RLS migration notice: %s", rls_err)

    elif dialect_name == "sqlite":
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(caravan_funding_opportunities)")).fetchall()
            existing_cols = {row[1] for row in result}
            sqlite_cols = [
                ("source_retrieval_at", "DATETIME"),
                ("verification_method", "VARCHAR(64) DEFAULT 'MANUAL_REGISTRY_AUDIT'"),
                ("verification_evidence", "JSON DEFAULT '{}'"),
                ("confidence_score", "FLOAT DEFAULT 1.0"),
                ("evidence_completeness", "VARCHAR(32) DEFAULT 'COMPLETE'"),
                ("last_checked_at", "DATETIME"),
                ("next_verification_at", "DATETIME"),
                ("verification_history", "JSON DEFAULT '[]'"),
                ("publication_status", "VARCHAR(32) DEFAULT 'PUBLISHED'"),
                ("official_application_url", "VARCHAR(500)"),
                ("supporting_source_urls", "JSON DEFAULT '[]'"),
                ("eligible_applicant_types", "JSON DEFAULT '[]'"),
                ("eligible_countries", "JSON DEFAULT '[]'"),
                ("eligible_states", "JSON DEFAULT '[]'"),
                ("eligible_sectors", "JSON DEFAULT '[]'"),
                ("funding_structure", "VARCHAR(120) DEFAULT 'DIRECT_DISBURSEMENT'"),
                ("business_stage", "VARCHAR(120) DEFAULT 'ALL_STAGES'"),
                ("age_restrictions", "VARCHAR(120) DEFAULT 'NO_RESTRICTION'"),
                ("registration_required", "BOOLEAN DEFAULT 1"),
                ("application_method", "VARCHAR(120) DEFAULT 'ONLINE_PORTAL'"),
                ("opportunity_status", "VARCHAR(64) DEFAULT 'OPEN'"),
                ("important_conditions", "TEXT DEFAULT ''"),
            ]
            for col_name, col_def in sqlite_cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE caravan_funding_opportunities ADD COLUMN {col_name} {col_def}"))
                    except Exception:
                        pass

            # SQLite compatibility columns for caravan_users
            try:
                user_cols_res = conn.execute(text("PRAGMA table_info(caravan_users)")).fetchall()
                existing_user_cols = {row[1] for row in user_cols_res}
                if "revoked_before_at" not in existing_user_cols:
                    conn.execute(text("ALTER TABLE caravan_users ADD COLUMN revoked_before_at DATETIME"))
                if "token_version" not in existing_user_cols:
                    conn.execute(text("ALTER TABLE caravan_users ADD COLUMN token_version INTEGER DEFAULT 1"))
            except Exception:
                pass



def run_migrations():
    """Ensure database tables are initialized and created, and migrate missing columns."""
    global _migrations_applied
    if _migrations_applied:
        return
    try:
        _execute_migrations()
        _migrations_applied = True
    except Exception as mig_exc:
        logger.warning("Database migration non-blocking warning: %s", mig_exc)

"""CARAVAN Standalone Platform — Database Session & PostgreSQL Connection Engine."""

from __future__ import annotations

import logging
import os
import urllib.parse
from pathlib import Path
from typing import Generator
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
    """Normalizes database URLs, sanitizes query parameters, and safely quotes credentials."""
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


def _try_alternate_pooler_port(db_url: str) -> str | None:
    """If connecting to Supabase pooler (*.pooler.supabase.com), toggle between 5432 and 6543."""
    from sqlalchemy.engine import make_url
    try:
        parsed = make_url(db_url)
        if parsed.host and "pooler.supabase.com" in parsed.host:
            current_port = parsed.port or 5432
            alt_port = 6543 if current_port == 5432 else 5432
            return parsed.set(port=alt_port).render_as_string(hide_password=False)
    except Exception:
        pass
    return None


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
        connect_args = {"connect_timeout": 5}
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

            # If Supabase pooler, attempt alternate port (5432 <-> 6543)
            alt_url = _try_alternate_pooler_port(db_url)
            if alt_url:
                try:
                    alt_engine = create_engine(
                        alt_url,
                        connect_args=connect_args,
                        **engine_kwargs,
                    )
                    with alt_engine.connect() as alt_conn:
                        alt_conn.execute(text("SELECT 1"))
                    _engine = alt_engine
                    logger.info("Connected successfully to primary PostgreSQL via alternate pooler port.")
                    return _engine
                except Exception as alt_exc:
                    logger.warning("Alternate pooler port attempt failed: %s", type(alt_exc).__name__)

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


def _execute_migrations():
    """Initializes tables and executes idempotent schema migrations."""
    engine = get_engine()
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
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
            ]
            for stmt in migration_statements:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
        elif dialect_name == "sqlite":
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

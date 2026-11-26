"""CARAVAN Standalone Platform — Database Session & Connection Pool."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None
_migrations_applied = False
_using_fallback = False
_primary_db_error = None
_fallback_seeded = False


def is_using_fallback() -> bool:
    global _using_fallback
    return _using_fallback


def get_primary_db_error() -> str | None:
    global _primary_db_error
    return _primary_db_error


def reset_engine():
    global _engine, _SessionLocal, _migrations_applied, _using_fallback, _primary_db_error, _fallback_seeded
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _migrations_applied = False
    _using_fallback = False
    _primary_db_error = None
    _fallback_seeded = False


def normalize_database_url(raw_url: str) -> str:
    cleaned = raw_url.strip() if raw_url else ""
    if not cleaned or cleaned.startswith("sqlite"):
        if not cleaned:
            cleaned = "sqlite:///./caravan.db"
        if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return "sqlite:////tmp/caravan.db"
        if cleaned.startswith("sqlite:///./") or cleaned == "sqlite:///caravan.db":
            # Resolve relative sqlite URL relative to backend directory or existing caravan.db
            backend_dir = Path(__file__).resolve().parents[2]
            backend_db = backend_dir / "caravan.db"
            if backend_db.exists():
                return f"sqlite:///{backend_db}"
            root_db = backend_dir.parent / "caravan.db"
            if root_db.exists() and root_db.stat().st_size > 0:
                return f"sqlite:///{root_db}"
            return f"sqlite:///{backend_db}"
        return cleaned
    candidate = cleaned
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


def get_engine():
    global _engine, _using_fallback, _primary_db_error
    if _engine is None:
        settings = get_settings()
        db_url = normalize_database_url(settings.DATABASE_URL)
        is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

        if not db_url.startswith("sqlite"):
            engine_kwargs = {"future": True}
            connect_args = {"connect_timeout": 3}
            if is_serverless:
                from sqlalchemy.pool import NullPool
                engine_kwargs["poolclass"] = NullPool
            else:
                engine_kwargs["pool_pre_ping"] = True

            try:
                candidate_engine = create_engine(
                    db_url,
                    connect_args=connect_args,
                    **engine_kwargs
                )
                with candidate_engine.connect() as test_conn:
                    test_conn.execute(text("SELECT 1"))
                _engine = candidate_engine
                _using_fallback = False
            except Exception as primary_exc:
                _primary_db_error = f"{type(primary_exc).__name__}: {primary_exc}"
                import logging
                logging.getLogger("caravan").warning(
                    "Primary database connection failed (%s). Activating resilient failover storage.",
                    primary_exc,
                )
                fallback_path = "/tmp/caravan.db" if is_serverless else "caravan_fallback.db"
                _engine = create_engine(
                    f"sqlite:///{fallback_path}",
                    connect_args={"check_same_thread": False, "timeout": 15},
                    future=True,
                )
                _using_fallback = True
        else:
            connect_args = {"check_same_thread": False, "timeout": 15}
            _engine = create_engine(
                db_url,
                connect_args=connect_args,
                future=True,
            )
            _using_fallback = False

    return _engine


def get_session_factory():
    global _SessionLocal, _migrations_applied, _using_fallback, _fallback_seeded
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine(), future=True)
        if not _migrations_applied:
            run_migrations()
        if _using_fallback and not _fallback_seeded:
            try:
                from app.seed_data import seed_caravan_opportunities
                with _SessionLocal() as sdb:
                    seed_caravan_opportunities(sdb)
                _fallback_seeded = True
            except Exception:
                pass
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _execute_migrations():
    engine = get_engine()
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Idempotent column migrations for evolved models
    with engine.begin() as conn:
        dialect_name = engine.dialect.name
        if dialect_name == "postgresql":
            # Add missing columns to caravan_funding_opportunities if absent
            migration_statements = [
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
                # caravan_organizations extensions
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

            org_res = conn.execute(text("PRAGMA table_info(caravan_organizations)")).fetchall()
            existing_org_cols = {row[1] for row in org_res}
            sqlite_org_cols = [
                ("annual_revenue_ngn", "FLOAT DEFAULT 0.0"),
                ("cac_registered", "BOOLEAN DEFAULT 1"),
                ("years_in_operation", "INTEGER DEFAULT 1"),
                ("female_led", "BOOLEAN DEFAULT 0"),
                ("youth_led", "BOOLEAN DEFAULT 1"),
                ("products_services", "TEXT DEFAULT ''"),
                ("target_customers", "VARCHAR(255) DEFAULT ''"),
                ("business_model", "VARCHAR(120) DEFAULT 'B2B'"),
                ("growth_objectives", "TEXT DEFAULT ''"),
                ("intended_use_of_funds", "TEXT DEFAULT ''"),
                ("previous_funding_history", "JSON DEFAULT '[]'"),
                ("readiness_score", "FLOAT DEFAULT 0.0"),
                ("readiness_breakdown", "JSON DEFAULT '{}'"),
            ]
            for col_name, col_def in sqlite_org_cols:
                if col_name not in existing_org_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE caravan_organizations ADD COLUMN {col_name} {col_def}"))
                    except Exception:
                        pass

        # Idempotent column migrations for caravan_documents
        if dialect_name == "postgresql":
            doc_stmts = [
                "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS storage_path VARCHAR(512)",
                "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS content_type VARCHAR(128) DEFAULT 'application/octet-stream'",
                "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS scan_status VARCHAR(32) DEFAULT 'AVAILABLE'",
                "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS scan_details JSON DEFAULT '{}'",
                "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS sha256_hash VARCHAR(64)",
                "ALTER TABLE caravan_documents ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
            ]
            for stmt in doc_stmts:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
        elif dialect_name == "sqlite":
            res = conn.execute(text("PRAGMA table_info(caravan_documents)")).fetchall()
            existing_doc_cols = {r[1] for r in res}
            sqlite_doc_cols = [
                ("storage_path", "VARCHAR(512)"),
                ("content_type", "VARCHAR(128) DEFAULT 'application/octet-stream'"),
                ("scan_status", "VARCHAR(32) DEFAULT 'AVAILABLE'"),
                ("scan_details", "JSON DEFAULT '{}'"),
                ("sha256_hash", "VARCHAR(64)"),
                ("deleted_at", "DATETIME"),
            ]
            for col_name, col_def in sqlite_doc_cols:
                if col_name not in existing_doc_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE caravan_documents ADD COLUMN {col_name} {col_def}"))
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
        import logging
        logging.getLogger("caravan").warning("Database migration non-blocking warning: %s", mig_exc)

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


def reset_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def normalize_database_url(raw_url: str) -> str:
    cleaned = raw_url.strip()
    if not cleaned or cleaned.startswith("sqlite"):
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
            parsed = parsed.set(query=filtered)
        return parsed.render_as_string(hide_password=False)
    except Exception:
        return candidate


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = normalize_database_url(settings.DATABASE_URL)
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine(), future=True)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Ensure database tables are initialized and created, and migrate missing columns."""
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
                ("source_retrieval_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ("verification_method", "VARCHAR(64) DEFAULT 'MANUAL_REGISTRY_AUDIT'"),
                ("verification_evidence", "JSON DEFAULT '{}'"),
                ("confidence_score", "FLOAT DEFAULT 1.0"),
                ("evidence_completeness", "VARCHAR(32) DEFAULT 'COMPLETE'"),
                ("last_checked_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ("next_verification_at", "DATETIME"),
                ("verification_history", "JSON DEFAULT '[]'"),
                ("publication_status", "VARCHAR(32) DEFAULT 'PUBLISHED'"),
            ]
            for col_name, col_def in sqlite_cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE caravan_funding_opportunities ADD COLUMN {col_name} {col_def}"))
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

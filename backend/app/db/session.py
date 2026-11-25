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


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.DATABASE_URL
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
    """Ensure database tables are initialized and created."""
    engine = get_engine()
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

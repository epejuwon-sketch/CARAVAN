"""CARAVAN Standalone Platform — Pytest Test Configuration & Fixtures."""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import Base, reset_engine, run_migrations, get_session_factory
from app.app_seed_helper import seed_test_database
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_file = tmp_path / "caravan_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("CARAVAN_ENV", "test")
    monkeypatch.setenv("ULTRON_BRIDGE_API_KEY", "test-ultron-s2s-bridge-key")

    get_settings.cache_clear()
    reset_engine()

    run_migrations()
    session_factory = get_session_factory()
    with session_factory() as db:
        seed_test_database(db)

    with TestClient(app) as test_client:
        yield test_client

    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def registered_customer(client: TestClient):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "founder@africanventures.com",
            "password": "StrongPassword2026!",
            "full_name": "Tariq Adeleke",
            "organization_name": "Adeleke AgriTech Solutions",
            "entity_type": "STARTUP",
            "country": "Nigeria",
            "state_location": "Abuja (FCT)",
            "sector": "AgriTech",
            "stage": "SEED",
        },
    )
    assert res.status_code == 201
    data = res.json()
    return {
        "token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
    }

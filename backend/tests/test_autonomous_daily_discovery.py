"""CARAVAN Standalone Platform — Autonomous Daily Funding Discovery Tests.

Validates the complete 8-step pipeline:
DISCOVER → EXTRACT → VALIDATE → VERIFY → DEDUPLICATE → CLASSIFY → PUBLISH → NOTIFY → MONITOR
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.db.models import (
    FundingOpportunityRecord,
    OrganizationRecord,
    UserRecord,
    NotificationRecord,
    AuditLogRecord,
    gen_id,
    utcnow,
)
from app.services.discovery_service import (
    DiscoveryEngine,
    DailyDiscoveryScheduler,
    is_trusted_institutional_domain,
    calculate_provenance_hash,
)
from app.core.security import create_access_token


def test_trusted_institutional_domain_verification():
    """Verify official institutional domain classification logic."""
    # Multilateral / DFI
    assert is_trusted_institutional_domain("https://www.afdb.org/en/topics-and-sectors/initiatives/sefa") is True
    assert is_trusted_institutional_domain("https://worldbank.org/en/programs") is True
    assert is_trusted_institutional_domain("https://ifc.org/solutions/funds") is True
    assert is_trusted_institutional_domain("https://fmo.nl/ventures") is True

    # Government / Sovereigns
    assert is_trusted_institutional_domain("https://boi.ng/funds/rural-area-dev") is True
    assert is_trusted_institutional_domain("https://nsia.com.ng/npi") is True
    assert is_trusted_institutional_domain("https://smedan.gov.ng/opportunities") is True
    assert is_trusted_institutional_domain("https://devbankng.com/initiatives") is True

    # Foundations & Climate Funds
    assert is_trusted_institutional_domain("https://tonyelumelufoundation.org/apply") is True
    assert is_trusted_institutional_domain("https://gatesfoundation.org/our-work") is True
    assert is_trusted_institutional_domain("https://greenclimate.fund/projects") is True

    # Commercial Banks & Corporate Programs
    assert is_trusted_institutional_domain("https://accessbankplc.com/w-power") is True
    assert is_trusted_institutional_domain("https://startup.google.com/black-founders") is True

    # Unverified / Arbitrary domains
    assert is_trusted_institutional_domain("https://random-free-grants-scam.xyz") is False
    assert is_trusted_institutional_domain("https://freefunding-blog.wordpress.com") is False
    assert is_trusted_institutional_domain("") is False


def test_monitored_sources_catalog():
    """Verify that the monitored institutional sources catalog contains multi-source coverage."""
    sources = DiscoveryEngine.list_monitored_sources()
    assert len(sources) >= 20, f"Expected at least 20 monitored sources, found {len(sources)}"

    categories = {s["category"] for s in sources}
    assert any("Multilateral" in c or "DFI" in c for c in categories)
    assert any("Grants" in c for c in categories)
    assert any("Federal" in c or "Central Bank" in c or "State" in c for c in categories)
    assert any("Credit" in c or "Lending" in c or "Finance" in c for c in categories)

    for src in sources:
        assert src["source_id"]
        assert src["name"]
        assert src["portal_url"].startswith("http")
        assert src["status"] == "OPERATIONAL"


def test_autonomous_daily_discovery_cycle(client: TestClient):
    """Test full execution of the 8-step daily autonomous discovery cycle."""
    session_factory = get_session_factory()
    with session_factory() as db:
        # 1. Run initial cycle
        results = DailyDiscoveryScheduler.execute_daily_cycle(db, actor="TEST_SCHEDULER")

        assert results["cycle_id"].startswith("dsc_cycle_")
        assert results["sources_monitored_count"] >= 20
        assert results["total_candidates"] >= 8
        assert results["ingested_count"] >= 8
        assert results["auto_published_count"] >= 6
        assert results["duplicate_skipped_count"] == 0

        # Verify ingested candidates have provenance hash and high confidence
        for det in results["details"]:
            opp = db.get(FundingOpportunityRecord, det["opportunity_id"])
            assert opp is not None
            assert opp.provenance_hash is not None
            assert len(opp.provenance_hash) == 64  # SHA-256
            assert opp.verification_evidence is not None
            assert opp.confidence_score >= 0.80
            assert opp.official_source_url is not None

        # Verify audit log was recorded
        audit = db.query(AuditLogRecord).filter_by(action="AUTONOMOUS_DAILY_DISCOVERY_COMPLETED").first()
        assert audit is not None
        assert audit.details["total_candidates"] == results["total_candidates"]

        # 2. Re-run cycle: deduplication should skip all already-ingested opportunities
        cycle_2 = DailyDiscoveryScheduler.execute_daily_cycle(db, actor="TEST_SCHEDULER_RERUN")
        assert cycle_2["ingested_count"] == 0
        assert cycle_2["duplicate_skipped_count"] == results["total_candidates"]


def test_enterprise_notification_dispatch_on_discovery(client: TestClient):
    """Verify that newly published opportunities trigger notifications for matched enterprises."""
    session_factory = get_session_factory()
    with session_factory() as db:
        # 1. Create registered enterprise organization and customer user
        org = OrganizationRecord(
            org_id=gen_id("org"),
            name="Solaris Agro CleanTech Ltd",
            country="Nigeria",
            state_location="Lagos",
            sector="CleanTech",
            stage="EARLY_GROWTH",
            annual_revenue_usd=50000.0,
            annual_revenue_ngn=50000000.0,
        )
        user = UserRecord(
            user_id=gen_id("usr"),
            organization_id=org.org_id,
            email="founder@solarisagro.ng",
            password_hash="mockhash",
            full_name="Amara Okafor",
            role="CUSTOMER",
            is_active=True,
        )
        db.add(org)
        db.add(user)
        db.commit()

        # 2. Ingest clean energy opportunity matching the enterprise sector
        clean_energy_candidate = {
            "title": "Africa Clean Energy Technical Assistance & Capital Grant 2026",
            "provider": "African Development Bank (AfDB)",
            "funding_type": "GRANT",
            "amount_min": 100000.0,
            "amount_max": 500000.0,
            "currency": "USD",
            "amount_display": "$100,000 – $500,000",
            "geographic_eligibility": "Sub-Saharan Africa",
            "applicant_eligibility": "Clean energy developers and commercial agro-energy ventures.",
            "industry_sector": "CleanTech",
            "eligible_sectors": ["CleanTech", "Agriculture", "Energy"],
            "eligible_countries": ["Nigeria", "Ghana", "Kenya"],
            "official_source_url": "https://www.afdb.org/en/topics-and-sectors/initiatives/sefa-2026",
            "auto_publish": True,
        }

        ingest_res = DiscoveryEngine.ingest_discovered_opportunity(
            db, clean_energy_candidate, discovered_by="AfDB_CRAWLER"
        )
        assert ingest_res["status"] == "INGESTED"
        opp_id = ingest_res["opportunity_id"]

        opp_rec = db.get(FundingOpportunityRecord, opp_id)
        notified_count = DiscoveryEngine.notify_matching_enterprises(db, opp_rec)
        assert notified_count >= 1

        # Verify notification record was persisted in database
        notifs = (
            db.query(NotificationRecord)
            .filter_by(user_id=user.user_id)
            .all()
        )
        assert len(notifs) >= 1
        target_notif = notifs[0]
        assert "Africa Clean Energy" in target_notif.title
        assert "CleanTech" in target_notif.message


def test_admin_daily_discovery_api(client: TestClient):
    """Test POST /api/v1/admin/intelligence/daily-run with admin authorization."""
    session_factory = get_session_factory()
    with session_factory() as db:
        admin_org = OrganizationRecord(
            org_id=gen_id("org"),
            name="CARAVAN Operations Admin Org",
            country="Nigeria",
            state_location="Abuja (FCT)",
            sector="Administration",
            stage="MATURE",
        )
        admin_user = UserRecord(
            user_id=gen_id("usr_adm"),
            organization_id=admin_org.org_id,
            email="chief.curator@caravanfunding.com",
            password_hash="mockhash",
            full_name="Chief Curator",
            role="SUPER_ADMIN",
            is_active=True,
        )
        admin_id = admin_user.user_id
        admin_email = admin_user.email
        db.add(admin_org)
        db.add(admin_user)
        db.commit()

    token = create_access_token({"sub": admin_id, "role": "SUPER_ADMIN", "email": admin_email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get sources
    sources_resp = client.get("/api/v1/admin/intelligence/sources", headers=headers)
    assert sources_resp.status_code == 200
    sources_data = sources_resp.json()
    assert "sources" in sources_data
    assert len(sources_data["sources"]) >= 20

    # 2. Trigger daily discovery cycle
    run_resp = client.post("/api/v1/admin/intelligence/daily-run", headers=headers)
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["cycle_id"].startswith("dsc_cycle_")
    assert run_data["total_candidates"] >= 8
    assert run_data["ingested_count"] >= 8


def test_cron_daily_discovery_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Test GET and POST /api/v1/cron/discovery with CRON_SECRET enforcement."""
    test_secret = "caravan_test_cron_secret_secure_token"
    monkeypatch.setenv("CRON_SECRET", test_secret)
    get_settings.cache_clear()

    # 1. Request without token should fail with 401
    unauth_resp = client.get("/api/v1/cron/discovery")
    assert unauth_resp.status_code == 401

    # 2. Request with invalid token should fail with 401
    bad_resp = client.get("/api/v1/cron/discovery", headers={"Authorization": "Bearer bad_secret"})
    assert bad_resp.status_code == 401

    # 3. Request with valid bearer token should succeed
    good_resp = client.post(
        "/api/v1/cron/discovery",
        headers={"Authorization": f"Bearer {test_secret}"},
    )
    assert good_resp.status_code == 200
    data = good_resp.json()
    assert data["status"] == "COMPLETED"
    assert data["job"] == "AUTONOMOUS_DAILY_FUNDING_DISCOVERY"
    assert "summary" in data
    assert data["summary"]["cycle_id"].startswith("dsc_cycle_")

    get_settings.cache_clear()

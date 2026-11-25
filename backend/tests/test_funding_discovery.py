"""CARAVAN Standalone Platform — Funding Intelligence & Discovery Unit Tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.models import FundingOpportunityRecord, OrganizationRecord, UserRecord, utcnow
from app.services.discovery_service import DiscoveryEngine, normalize_url, calculate_provenance_hash


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()


def test_url_normalization():
    url1 = "https://www.tonyelumelufoundation.org/programmes?utm_source=test#apply"
    url2 = "https://www.tonyelumelufoundation.org/programmes/"
    assert normalize_url(url1) == "https://www.tonyelumelufoundation.org/programmes"
    assert normalize_url(url2) == "https://www.tonyelumelufoundation.org/programmes"


def test_provenance_hash_determinism():
    item1 = {
        "title": "Tony Elumelu Foundation Grant",
        "provider": "Tony Elumelu Foundation",
        "official_source_url": "https://tonyelumelufoundation.org/programmes",
    }
    item2 = {
        "title": " tony elumelu foundation grant ",
        "provider": "Tony Elumelu Foundation ",
        "official_source_url": "https://tonyelumelufoundation.org/programmes/",
    }
    assert calculate_provenance_hash(item1) == calculate_provenance_hash(item2)


def test_discovery_ingestion_and_review_workflow(test_db):
    raw_candidate = {
        "title": "Google for Startups Black Founders Fund",
        "provider": "Google for Startups",
        "official_source_url": "https://startup.google.com/programs/black-founders-fund/",
        "funding_type": "GRANT",
        "amount_min": 50000.0,
        "amount_max": 100000.0,
        "currency": "USD",
        "amount_display": "$50,000 - $100,000 non-dilutive grant",
        "geographic_eligibility": "Sub-Saharan Africa",
        "applicant_eligibility": "Black-led tech startups at seed or early stage",
        "industry_sector": "Technology",
        "application_requirements": ["Product pitch deck", "Traction metrics"],
        "is_rolling": False,
        "source_name": "Google Developers Registry",
    }

    # Ingest candidate
    ingest_res = DiscoveryEngine.ingest_discovered_opportunity(test_db, raw_candidate, discovered_by="SUBAGENT_TEST")
    assert ingest_res["status"] == "INGESTED"
    opp_id = ingest_res["opportunity_id"]
    assert ingest_res["publication_status"] == "PENDING_REVIEW"
    assert ingest_res["confidence_score"] >= 0.7

    # Duplicate detection on re-ingestion
    dup_res = DiscoveryEngine.ingest_discovered_opportunity(test_db, raw_candidate, discovered_by="SUBAGENT_TEST")
    assert dup_res["status"] == "DUPLICATE"
    assert dup_res["opportunity_id"] == opp_id

    # Queue inspection
    queue = DiscoveryEngine.get_review_queue(test_db)
    assert len(queue) == 1
    assert queue[0]["opportunity_id"] == opp_id

    # Approve and publish
    approve_res = DiscoveryEngine.approve_opportunity(
        test_db,
        opportunity_id=opp_id,
        reviewer_id="reviewer_001",
        reviewer_role="SUPER_ADMIN",
        notes="Verified against Google for Startups official portal.",
    )
    assert approve_res["success"] is True
    assert approve_res["status"] == "PUBLISHED"

    # Verify published record in DB
    record = test_db.get(FundingOpportunityRecord, opp_id)
    assert record.publication_status == "PUBLISHED"
    assert record.verification_status in {"VERIFIED", "VERIFIED_OPEN"}
    assert record.confidence_score == 1.0
    assert len(record.verification_history) == 2


def test_discovery_rejection_workflow(test_db):
    raw_invalid = {
        "title": "Expired Private Bounty",
        "provider": "Unverified Entity",
        "official_source_url": "https://unverified.example.com/bounty",
        "funding_type": "GRANT",
    }
    ingest_res = DiscoveryEngine.ingest_discovered_opportunity(test_db, raw_invalid, discovered_by="CRAWLER")
    assert ingest_res["status"] == "INGESTED"
    opp_id = ingest_res["opportunity_id"]

    reject_res = DiscoveryEngine.reject_opportunity(
        test_db,
        opportunity_id=opp_id,
        reviewer_id="reviewer_002",
        reviewer_role="OPPORTUNITY_REVIEWER",
        reason="Source domain unverified and dead link.",
    )
    assert reject_res["success"] is True
    assert reject_res["status"] == "ARCHIVED"

    record = test_db.get(FundingOpportunityRecord, opp_id)
    assert record.publication_status == "ARCHIVED"
    assert record.verification_status == "REJECTED"

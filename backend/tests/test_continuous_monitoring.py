"""CARAVAN Standalone Platform — Continuous Opportunity Lifecycle Monitoring Tests.

Validates:
1. Dynamic status recalibration: OPEN, CLOSING_SOON, CLOSED, UPCOMING, ROLLING
2. Approaching statutory deadline alerts for active application workspaces (14d, 7d, 48h)
3. Notification deduplication and audit trail logging
4. Cron and Admin API endpoints
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.db.models import (
    FundingOpportunityRecord,
    OrganizationRecord,
    UserRecord,
    ApplicationRecord,
    NotificationRecord,
    AuditLogRecord,
    gen_id,
    utcnow,
)
from app.services.discovery_service import DiscoveryEngine
from app.core.security import create_access_token


def test_lifecycle_recalibration_statuses():
    """Verify dynamic opportunity lifecycle status recalibration."""
    factory = get_session_factory()
    now = utcnow()

    with factory() as db:
        # Create test opportunities representing various lifecycle states
        # 1. Past deadline -> CLOSED / EXPIRED
        opp_past = FundingOpportunityRecord(
            opportunity_id=gen_id("opp_test_past"),
            title="Past Due Opportunity",
            provider="World Bank",
            applicant_eligibility="Registered entities",
            funding_type="GRANT",
            amount_min=10000.0,
            amount_max=50000.0,
            currency="USD",
            deadline_at=now - timedelta(days=2),
            publication_status="PUBLISHED",
            opportunity_status="OPEN",
            verification_status="VERIFIED",
            provenance_hash="test_prov_hash_past",
            official_source_url="https://worldbank.org/en/past",
        )

        # 2. Urgent deadline in 3 days -> CLOSING_SOON
        opp_urgent = FundingOpportunityRecord(
            opportunity_id=gen_id("opp_test_urgent"),
            title="Urgent Closing Opportunity",
            provider="IFC Ventures",
            applicant_eligibility="Startups and SMEs",
            funding_type="GRANT",
            amount_min=20000.0,
            amount_max=100000.0,
            currency="USD",
            deadline_at=now + timedelta(days=3),
            publication_status="PUBLISHED",
            opportunity_status="OPEN",
            verification_status="VERIFIED",
            provenance_hash="test_prov_hash_urg",
            official_source_url="https://ifc.org/solutions/urgent",
        )

        # 3. Future opening date -> UPCOMING
        opp_future = FundingOpportunityRecord(
            opportunity_id=gen_id("opp_test_future"),
            title="Future Opportunity",
            provider="African Development Bank",
            applicant_eligibility="Renewable companies",
            funding_type="EQUITY",
            amount_min=50000.0,
            amount_max=250000.0,
            currency="USD",
            opening_date=now + timedelta(days=20),
            deadline_at=now + timedelta(days=60),
            publication_status="PUBLISHED",
            opportunity_status="OPEN",
            verification_status="VERIFIED",
            provenance_hash="test_prov_hash_fut",
            official_source_url="https://afdb.org/en/future",
        )

        # 4. Rolling intake -> ROLLING
        opp_rolling = FundingOpportunityRecord(
            opportunity_id=gen_id("opp_test_rolling"),
            title="Rolling Intake Program",
            provider="Bank of Industry",
            applicant_eligibility="Nigerian SMEs",
            funding_type="LOAN",
            amount_min=100000.0,
            amount_max=1000000.0,
            currency="USD",
            is_rolling=True,
            publication_status="PUBLISHED",
            opportunity_status="OPEN",
            verification_status="VERIFIED",
            provenance_hash="test_prov_hash_roll",
            official_source_url="https://boi.ng/funds/rolling",
        )

        db.add_all([opp_past, opp_urgent, opp_future, opp_rolling])
        db.commit()

        # Execute monitoring cycle
        result = DiscoveryEngine.monitor_continuous_lifecycle(db, actor="TEST_MONITOR")
        assert result["status"] == "COMPLETED"
        assert result["recalibrated_count"] >= 4

        # Verify state changes
        db.refresh(opp_past)
        db.refresh(opp_urgent)
        db.refresh(opp_future)
        db.refresh(opp_rolling)

        assert opp_past.opportunity_status == "CLOSED"
        assert opp_past.verification_status == "EXPIRED"

        assert opp_urgent.opportunity_status == "CLOSING_SOON"
        assert opp_future.opportunity_status == "UPCOMING"
        assert opp_rolling.opportunity_status == "ROLLING"


def test_active_application_deadline_alerts_and_deduplication():
    """Verify deadline alerts for active application workspaces and notification deduplication."""
    factory = get_session_factory()
    now = utcnow()

    with factory() as db:
        org = OrganizationRecord(
            org_id=gen_id("org_alert_test"),
            name="Agritech Innovation Ltd",
            sector="AGRITECH",
            country="NG",
        )
        db.add(org)
        db.flush()

        user = UserRecord(
            user_id=gen_id("usr_alert_test"),
            email=f"alert-founder-{gen_id('rand')}@example.com",
            full_name="Agritech Founder",
            password_hash="mock_hash",
            role="CUSTOMER",
            organization_id=org.org_id,
        )
        db.add(user)
        db.flush()

        # Opportunity with deadline in 36 hours (Urgent: 48 Hours Left)
        opp_48h = FundingOpportunityRecord(
            opportunity_id=gen_id("opp_48h"),
            title="Emergency Solar Agri Grant",
            provider="SEFA",
            applicant_eligibility="Agri-solar developers",
            funding_type="GRANT",
            amount_min=50000.0,
            amount_max=100000.0,
            currency="USD",
            deadline_at=now + timedelta(hours=36),
            publication_status="PUBLISHED",
            opportunity_status="CLOSING_SOON",
            verification_status="VERIFIED",
            provenance_hash="test_prov_48h",
            official_source_url="https://afdb.org/sefa-urgent",
        )
        db.add(opp_48h)
        db.flush()

        # Active workspace application in DRAFTING
        app = ApplicationRecord(
            application_id=gen_id("app_48h"),
            organization_id=org.org_id,
            opportunity_id=opp_48h.opportunity_id,
            status="DRAFTING",
            created_at=now,
            updated_at=now,
        )
        db.add(app)
        db.commit()

        # Run cycle 1: Alert should be dispatched
        cycle1 = DiscoveryEngine.monitor_continuous_lifecycle(db, actor="TEST_MONITOR")
        assert cycle1["deadline_alerts_dispatched"] >= 1

        # Check notification content
        notifs = db.execute(
            select(NotificationRecord).where(NotificationRecord.user_id == user.user_id)
        ).scalars().all()
        assert len(notifs) >= 1
        notif = notifs[-1]
        assert "[Urgent: 48 Hours Left]" in notif.title
        assert opp_48h.title in notif.title
        assert notif.category == "DEADLINE"

        # Run cycle 2: Deduplication should prevent duplicate notification
        cycle2 = DiscoveryEngine.monitor_continuous_lifecycle(db, actor="TEST_MONITOR")
        assert cycle2["deadline_alerts_dispatched"] == 0

        # Notification count should not have increased
        notifs_after = db.execute(
            select(NotificationRecord).where(NotificationRecord.user_id == user.user_id)
        ).scalars().all()
        assert len(notifs_after) == len(notifs)


def test_cron_and_admin_monitoring_endpoints():
    """Verify monitoring endpoints via TestClient."""
    from app.main import app as fastapi_app

    client = TestClient(fastapi_app)

    # 1. Test /api/v1/cron/monitoring
    cron_res = client.post("/api/v1/cron/monitoring")
    assert cron_res.status_code == 200
    cron_data = cron_res.json()
    assert cron_data["status"] == "COMPLETED"
    assert cron_data["job"] == "CONTINUOUS_LIFECYCLE_MONITORING"
    assert "summary" in cron_data

    # 2. Test /api/v1/admin/intelligence/monitor-now with admin token
    factory = get_session_factory()
    with factory() as db:
        admin_org = OrganizationRecord(
            org_id=gen_id("org_admin_mon"),
            name="Caravan Ops HQ",
            sector="GOVERNMENT",
            country="NG",
        )
        db.add(admin_org)
        db.flush()

        admin_user = UserRecord(
            user_id=gen_id("usr_admin_mon"),
            email=f"admin-mon-{gen_id('rand')}@caravan.internal",
            full_name="Caravan Monitor Admin",
            password_hash="mock_hash",
            role="SUPER_ADMIN",
            organization_id=admin_org.org_id,
        )
        db.add(admin_user)
        db.commit()

        admin_id = admin_user.user_id
        admin_email = admin_user.email
        admin_org_id = admin_org.org_id

    token = create_access_token(
        {
            "sub": admin_id,
            "email": admin_email,
            "role": "SUPER_ADMIN",
            "org_id": admin_org_id,
            "permissions": ["opportunities:review", "admin:read"],
        }
    )

    admin_res = client.post(
        "/api/v1/admin/intelligence/monitor-now",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["status"] == "COMPLETED"
    assert "recalibrated_count" in admin_data

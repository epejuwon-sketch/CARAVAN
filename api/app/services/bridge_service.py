"""CARAVAN Standalone Platform — Scoped S2S Bridge for ULTRON Operations Center."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.db.models import (
    UserRecord,
    OrganizationRecord,
    FundingOpportunityRecord,
    ApplicationRecord,
    SubscriptionRecord,
    PaymentTransactionRecord,
    SupportTicketRecord,
    AuditLogRecord,
)


def get_caravan_operations_telemetry(db: Session) -> Dict[str, Any]:
    """Provide comprehensive, un-fabricated operational metrics to ULTRON Operations Center."""
    now = datetime.now(timezone.utc)

    # 1. Accounts & Organizations
    total_users = db.execute(select(func.count(UserRecord.user_id))).scalar() or 0
    total_orgs = db.execute(select(func.count(OrganizationRecord.org_id))).scalar() or 0

    # 2. Opportunities by status
    total_opps = db.execute(select(func.count(FundingOpportunityRecord.opportunity_id))).scalar() or 0
    verified_opps = db.execute(
        select(func.count(FundingOpportunityRecord.opportunity_id)).where(
            FundingOpportunityRecord.verification_status.in_(["VERIFIED", "VERIFIED_OPEN"])
        )
    ).scalar() or 0
    upcoming_opps = db.execute(
        select(func.count(FundingOpportunityRecord.opportunity_id)).where(
            FundingOpportunityRecord.verification_status.in_(["UPCOMING", "UPCOMING_CONFIRMED"])
        )
    ).scalar() or 0
    closed_opps = db.execute(
        select(func.count(FundingOpportunityRecord.opportunity_id)).where(FundingOpportunityRecord.verification_status == "CLOSED")
    ).scalar() or 0
    unverified_opps = db.execute(
        select(func.count(FundingOpportunityRecord.opportunity_id)).where(
            FundingOpportunityRecord.verification_status.in_(["UNVERIFIED", "NEEDS_REVIEW", "PENDING_REVIEW"])
        )
    ).scalar() or 0
    expired_opps = db.execute(
        select(func.count(FundingOpportunityRecord.opportunity_id)).where(FundingOpportunityRecord.verification_status == "EXPIRED")
    ).scalar() or 0

    # 3. Application pipelines
    total_apps = db.execute(select(func.count(ApplicationRecord.application_id))).scalar() or 0
    apps_drafting = db.execute(
        select(func.count(ApplicationRecord.application_id)).where(ApplicationRecord.status == "DRAFTING")
    ).scalar() or 0
    apps_submitted = db.execute(
        select(func.count(ApplicationRecord.application_id)).where(ApplicationRecord.status == "SUBMITTED")
    ).scalar() or 0
    apps_awarded = db.execute(
        select(func.count(ApplicationRecord.application_id)).where(ApplicationRecord.status == "AWARDED")
    ).scalar() or 0

    # 4. Subscriptions
    total_subs = db.execute(select(func.count(SubscriptionRecord.subscription_id))).scalar() or 0
    active_subs = db.execute(
        select(func.count(SubscriptionRecord.subscription_id)).where(SubscriptionRecord.status == "ACTIVE")
    ).scalar() or 0

    # 5. Financial volume (Sandbox transactions)
    total_tx_count = db.execute(select(func.count(PaymentTransactionRecord.tx_id))).scalar() or 0
    total_tx_amount = db.execute(select(func.sum(PaymentTransactionRecord.amount))).scalar() or 0.0

    # 6. Support Tickets
    open_tickets = db.execute(
        select(func.count(SupportTicketRecord.ticket_id)).where(SupportTicketRecord.status == "OPEN")
    ).scalar() or 0

    # 7. Recent Audit Log Activity
    recent_logs = db.execute(
        select(AuditLogRecord).order_by(desc(AuditLogRecord.created_at)).limit(15)
    ).scalars().all()

    timeline = [
        {
            "id": log.log_id,
            "timestamp": log.created_at.isoformat(),
            "actor": log.actor,
            "action": log.action,
            "resource": log.resource,
            "outcome": log.outcome,
            "details": log.details,
        }
        for log in recent_logs
    ]

    return {
        "status": "HEALTHY",
        "service": "CARAVAN Standalone Platform",
        "version": "1.0.0-production",
        "timestamp": now.isoformat(),
        "database": "CONNECTED",
        "security_identity": "AEGIS",
        "customers": {
            "total_users": total_users,
            "total_organizations": total_orgs,
            "active_subscriptions": active_subs,
            "total_subscriptions": total_subs,
        },
        "funding_intelligence": {
            "total_opportunities": total_opps,
            "verified_count": verified_opps,
            "upcoming_count": upcoming_opps,
            "closed_count": closed_opps,
            "unverified_count": unverified_opps,
            "expired_count": expired_opps,
        },
        "application_pipeline": {
            "total_applications": total_apps,
            "drafting_count": apps_drafting,
            "submitted_count": apps_submitted,
            "awarded_count": apps_awarded,
        },
        "financial_overview": {
            "transaction_count": total_tx_count,
            "total_volume_ngn": total_tx_amount,
            "payment_gateway_mode": "SANDBOX_READY",
        },
        "support": {
            "open_tickets": open_tickets,
        },
        "audit_timeline": timeline,
    }


def execute_bridge_sweep_expired(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    expired_records = db.execute(
        select(FundingOpportunityRecord).where(
            FundingOpportunityRecord.verification_status == "VERIFIED",
            FundingOpportunityRecord.is_rolling.is_(False),
            FundingOpportunityRecord.deadline_at.is_not(None),
            FundingOpportunityRecord.deadline_at < now,
        )
    ).scalars().all()

    count = 0
    for r in expired_records:
        r.verification_status = "EXPIRED"
        count += 1

    if count > 0:
        audit = AuditLogRecord(
            actor="svc_ultron_operations",
            action="SWEEP_EXPIRED_OPPORTUNITIES",
            resource="funding_opportunities",
            details={"swept_count": count},
        )
        db.add(audit)
        db.commit()

    return {"status": "SUCCESS", "swept_count": count}

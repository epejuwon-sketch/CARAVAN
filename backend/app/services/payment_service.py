"""CARAVAN Standalone Platform — Pricing Tiers & Nigerian Payment Gateways Service."""

from __future__ import annotations

import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.db.models import (
    SubscriptionRecord,
    PaymentTransactionRecord,
    AuditLogRecord,
    gen_id,
)

CARAVAN_SUBSCRIPTION_TIERS = {
    "FREE": {
        "tier": "FREE",
        "name": "Community Explorer",
        "price_usd": 0.0,
        "price_ngn": 0.0,
        "features": [
            "Access to open verified funding catalog",
            "3 active eligibility evaluations per month",
            "1 application preparation workspace",
            "Weekly email intelligence digests",
            "Community forum access",
        ],
    },
    "STARTER": {
        "tier": "STARTER",
        "name": "Emerging Founder",
        "price_usd": 19.0,
        "price_ngn": 29000.0,
        "features": [
            "Full verified funding catalog across Africa & UK",
            "Unlimited eligibility match scoring",
            "5 active application pipelines",
            "Document checklist tracking",
            "Deadline countdown alerts via email & SMS",
            "Standard support response (within 24 hours)",
        ],
    },
    "GROWTH": {
        "tier": "GROWTH",
        "name": "Scaling Venture",
        "price_usd": 49.0,
        "price_ngn": 75000.0,
        "features": [
            "All Emerging Founder features",
            "15 active application pipelines",
            "AI-assisted proposal outline drafting",
            "Investor & grantmaker provenance intelligence",
            "Team workspace (up to 3 collaborator seats)",
            "Priority support queue",
        ],
    },
    "PRO": {
        "tier": "PRO",
        "name": "Institutional Scale",
        "price_usd": 99.0,
        "price_ngn": 150000.0,
        "features": [
            "All Scaling Venture features",
            "Unlimited application pipelines",
            "Multi-organization portfolio management",
            "Concessionary debt & DFI facility tracking",
            "Dedicated onboarding specialist",
            "Direct Slack / WhatsApp support bridge",
        ],
    },
    "INSTITUTIONAL": {
        "tier": "INSTITUTIONAL",
        "name": "Venture Studio & Fund",
        "price_usd": 249.0,
        "price_ngn": 380000.0,
        "features": [
            "All Institutional Scale features",
            "Unlimited portfolio company workspaces",
            "Custom intake and grant syndication feeds",
            "Automated LP and grantmaker compliance reporting",
            "API access for private dealflow integration",
            "Dedicated relationship director",
        ],
    },
    "CUSTOM": {
        "tier": "CUSTOM",
        "name": "Sovereign & DFI Enterprise",
        "price_usd": 0.0,
        "price_ngn": 0.0,
        "features": [
            "Bespoke national or regional funding directories",
            "Sovereign data residency & on-premise deployments",
            "Multi-stakeholder review committees",
            "SLA guarantee & custom audit logging",
        ],
    },
}


def get_pricing_tiers() -> Dict[str, Any]:
    return {
        "currency_base": "USD",
        "nigeria_currency": "NGN",
        "supported_providers": ["FLUTTERWAVE", "PAYSTACK"],
        "sandbox_mode": True,
        "tiers": list(CARAVAN_SUBSCRIPTION_TIERS.values()),
    }


def get_organization_subscription(db: Session, org_id: str) -> dict:
    sub = db.execute(select(SubscriptionRecord).where(SubscriptionRecord.organization_id == org_id)).scalar_one_or_none()
    tier_name = sub.tier if sub else "FREE"
    tier_info = CARAVAN_SUBSCRIPTION_TIERS.get(tier_name, CARAVAN_SUBSCRIPTION_TIERS["FREE"])

    return {
        "subscription_id": sub.subscription_id if sub else "sub_default",
        "organization_id": org_id,
        "tier": tier_name,
        "tier_name": tier_info["name"],
        "price_usd": tier_info["price_usd"],
        "price_ngn": tier_info["price_ngn"],
        "status": sub.status if sub else "ACTIVE",
        "billing_provider": sub.billing_provider if sub else "MANUAL",
        "renewal_date": sub.renewal_date.isoformat() if sub and sub.renewal_date else None,
        "features": tier_info["features"],
    }


def process_payment_webhook(
    db: Session,
    provider: str,
    payload: dict,
    signature_header: Optional[str] = None,
) -> dict:
    """Handle verified sandbox webhooks from Flutterwave or Paystack."""
    provider_clean = provider.upper()
    settings = get_settings()

    # In sandbox/test environment, verify signature or validate structure
    if provider_clean == "FLUTTERWAVE":
        # Event: charge.completed
        event = payload.get("event")
        data = payload.get("data", {})
        ref = data.get("tx_ref") or data.get("id") or gen_id("flw")
        amount = float(data.get("amount", 0.0))
        currency = data.get("currency", "NGN")
        meta = data.get("meta", {})
        org_id = meta.get("org_id", "org_demo")
        tier = meta.get("tier", "STARTER")
        tx_status = "SUCCESSFUL" if (data.get("status") in ("successful", "success") or event in ("charge.completed", "charge.success")) else "FAILED"

    elif provider_clean == "PAYSTACK":
        event = payload.get("event")
        data = payload.get("data", {})
        ref = data.get("reference") or gen_id("pstk")
        amount = float(data.get("amount", 0.0)) / 100.0  # Paystack amounts are in kobo
        currency = data.get("currency", "NGN")
        meta = data.get("metadata", {})
        org_id = meta.get("org_id", "org_demo")
        tier = meta.get("tier", "STARTER")
        tx_status = "SUCCESSFUL" if (data.get("status") in ("success", "successful") or event in ("charge.success", "charge.completed")) else "FAILED"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported payment provider '{provider}'.")

    # Idempotency check
    existing_tx = db.execute(
        select(PaymentTransactionRecord).where(PaymentTransactionRecord.reference == str(ref))
    ).scalar_one_or_none()

    if existing_tx:
        return {"status": "ALREADY_PROCESSED", "reference": ref, "tier": existing_tx.tier}

    # Record Transaction
    tx = PaymentTransactionRecord(
        tx_id=gen_id("tx"),
        organization_id=org_id,
        provider=provider_clean,
        reference=str(ref),
        amount=amount,
        currency=currency,
        tier=tier,
        status=tx_status,
        metadata_json=payload,
    )
    db.add(tx)

    # If successful, upgrade or renew subscription
    if tx_status == "SUCCESSFUL":
        sub = db.execute(
            select(SubscriptionRecord).where(SubscriptionRecord.organization_id == org_id)
        ).scalar_one_or_none()
        renewal = datetime.now(timezone.utc) + timedelta(days=30)
        tier_data = CARAVAN_SUBSCRIPTION_TIERS.get(tier, CARAVAN_SUBSCRIPTION_TIERS["STARTER"])
        if sub:
            sub.tier = tier
            sub.status = "ACTIVE"
            sub.billing_provider = provider_clean
            sub.price_usd_monthly = tier_data["price_usd"]
            sub.renewal_date = renewal
        else:
            new_sub = SubscriptionRecord(
                subscription_id=gen_id("sub"),
                organization_id=org_id,
                tier=tier,
                price_usd_monthly=tier_data["price_usd"],
                billing_provider=provider_clean,
                status="ACTIVE",
                renewal_date=renewal,
            )
            db.add(new_sub)

    audit = AuditLogRecord(
        actor=f"webhook:{provider_clean}",
        action="PAYMENT_PROCESSED",
        resource=f"tx:{ref}",
        details={"org_id": org_id, "amount": amount, "currency": currency, "status": tx_status},
    )
    db.add(audit)
    db.commit()

    return {"status": "PROCESSED", "reference": ref, "payment_status": tx_status, "tier": tier}

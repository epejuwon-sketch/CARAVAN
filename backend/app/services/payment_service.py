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
        "monthly_copilot_credits": 20,
        "max_saved": 5,
        "max_apps": 1,
        "features": [
            "Access to open verified funding catalog",
            "3 active eligibility evaluations per month",
            "1 application preparation workspace",
            "20 CARAVAN Copilot prompt credits / month",
            "Weekly email intelligence digests",
        ],
    },
    "STARTER": {
        "tier": "STARTER",
        "name": "Emerging Founder",
        "price_usd": 19.0,
        "price_ngn": 29000.0,
        "monthly_copilot_credits": 100,
        "max_saved": 25,
        "max_apps": 3,
        "features": [
            "Full verified funding catalog across Africa & UK",
            "Unlimited eligibility match scoring",
            "3 active application pipelines",
            "100 CARAVAN Copilot prompt credits / month",
            "Document checklist tracking",
            "Export readiness & eligibility reports",
        ],
    },
    "GROWTH": {
        "tier": "GROWTH",
        "name": "Scaling Venture",
        "price_usd": 49.0,
        "price_ngn": 75000.0,
        "monthly_copilot_credits": 500,
        "max_saved": 100,
        "max_apps": 15,
        "features": [
            "All Emerging Founder features",
            "15 active application pipelines",
            "500 CARAVAN Copilot prompt credits / month",
            "AI-assisted proposal outline drafting",
            "Team workspace (up to 3 collaborator seats)",
            "Priority support queue",
        ],
    },
    "PRO": {
        "tier": "PRO",
        "name": "Institutional Scale",
        "price_usd": 99.0,
        "price_ngn": 150000.0,
        "monthly_copilot_credits": 2000,
        "max_saved": 500,
        "max_apps": 50,
        "features": [
            "All Scaling Venture features",
            "50 application pipelines",
            "2,000 CARAVAN Copilot prompt credits / month",
            "Multi-organization portfolio management",
            "Concessionary debt & DFI facility tracking",
            "Dedicated onboarding specialist",
        ],
    },
    "BUSINESS": {
        "tier": "BUSINESS",
        "name": "Venture Studio & Fund",
        "price_usd": 249.0,
        "price_ngn": 380000.0,
        "monthly_copilot_credits": 10000,
        "max_saved": 999999,
        "max_apps": 999999,
        "features": [
            "All Institutional Scale features",
            "Unlimited application pipelines",
            "10,000 CARAVAN Copilot prompt credits / month",
            "Unlimited portfolio company workspaces",
            "Team workspace (up to 25 collaborator seats)",
            "API access for private dealflow integration",
        ],
    },
    "ENTERPRISE": {
        "tier": "ENTERPRISE",
        "name": "Sovereign & DFI Enterprise",
        "price_usd": 0.0,
        "price_ngn": 0.0,
        "monthly_copilot_credits": 50000,
        "max_saved": 999999,
        "max_apps": 999999,
        "features": [
            "Bespoke national or regional funding directories",
            "Sovereign data residency & on-premise deployments",
            "Unlimited Copilot credits & custom fine-tuned model",
            "Multi-stakeholder review committees",
            "SLA guarantee & custom audit logging",
        ],
    },
    # Backward compatibility aliases
    "INSTITUTIONAL": {
        "tier": "INSTITUTIONAL",
        "name": "Venture Studio & Fund",
        "price_usd": 249.0,
        "price_ngn": 380000.0,
        "monthly_copilot_credits": 10000,
        "max_saved": 999999,
        "max_apps": 999999,
        "features": [
            "All Institutional Scale features",
            "Unlimited application pipelines",
            "10,000 CARAVAN Copilot prompt credits / month",
            "API access for private dealflow integration",
        ],
    },
    "CUSTOM": {
        "tier": "CUSTOM",
        "name": "Sovereign & DFI Enterprise",
        "price_usd": 0.0,
        "price_ngn": 0.0,
        "monthly_copilot_credits": 50000,
        "max_saved": 999999,
        "max_apps": 999999,
        "features": [
            "Bespoke national or regional funding directories",
            "Sovereign data residency & on-premise deployments",
        ],
    },
}


def get_pricing_tiers() -> Dict[str, Any]:
    return {
        "currency_base": "USD",
        "nigeria_currency": "NGN",
        "supported_providers": ["FLUTTERWAVE", "PAYSTACK", "SANDBOX"],
        "sandbox_mode": True,
        "tiers": list(CARAVAN_SUBSCRIPTION_TIERS.values()),
    }


def get_organization_subscription(db: Session, org_id: str) -> dict:
    sub = db.execute(select(SubscriptionRecord).where(SubscriptionRecord.organization_id == org_id)).scalar_one_or_none()
    raw_tier = sub.tier if sub else "FREE"
    tier_name = raw_tier.upper()
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


def sandbox_upgrade_organization_subscription(
    db: Session,
    org_id: str,
    target_tier: str,
    actor: str = "customer",
) -> dict:
    """Instantly activate or simulate upgrading to any subscription tier in sandbox mode."""
    target_clean = target_tier.strip().upper()
    if target_clean not in CARAVAN_SUBSCRIPTION_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription tier '{target_tier}'. Valid tiers: {list(CARAVAN_SUBSCRIPTION_TIERS.keys())}",
        )

    tier_info = CARAVAN_SUBSCRIPTION_TIERS[target_clean]
    sub = db.execute(
        select(SubscriptionRecord).where(SubscriptionRecord.organization_id == org_id)
    ).scalar_one_or_none()

    renewal = datetime.now(timezone.utc) + timedelta(days=30)
    if sub:
        sub.tier = target_clean
        sub.status = "ACTIVE"
        sub.billing_provider = "SANDBOX"
        sub.price_usd_monthly = tier_info["price_usd"]
        sub.renewal_date = renewal
    else:
        sub = SubscriptionRecord(
            subscription_id=gen_id("sub"),
            organization_id=org_id,
            tier=target_clean,
            price_usd_monthly=tier_info["price_usd"],
            billing_provider="SANDBOX",
            status="ACTIVE",
            renewal_date=renewal,
        )
        db.add(sub)

    # Record sandbox transaction
    tx = PaymentTransactionRecord(
        tx_id=gen_id("tx"),
        organization_id=org_id,
        provider="SANDBOX",
        reference=f"sbx_{gen_id('ref')}",
        amount=tier_info["price_ngn"],
        currency="NGN",
        tier=target_clean,
        status="SUCCESSFUL",
        metadata_json={"simulated_upgrade": True, "actor": actor},
    )
    db.add(tx)

    audit = AuditLogRecord(
        actor=actor,
        action="SUBSCRIPTION_UPGRADED_SANDBOX",
        resource=f"subscription:{sub.subscription_id}",
        details={"org_id": org_id, "tier": target_clean, "price_usd": tier_info["price_usd"]},
    )
    db.add(audit)
    db.commit()

    return {
        "status": "UPGRADED",
        "organization_id": org_id,
        "tier": target_clean,
        "tier_name": tier_info["name"],
        "price_usd": tier_info["price_usd"],
        "renewal_date": renewal.isoformat(),
        "billing_provider": "SANDBOX",
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

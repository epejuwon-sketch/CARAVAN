"""CARAVAN Standalone Platform — Central Entitlement Matrix & Quota Controller.

Enforces subscription tier quotas, feature flags, usage tracking, and multi-tenant billing
boundaries across the entire CARAVAN application.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import (
    SubscriptionRecord,
    SavedOpportunityRecord,
    ApplicationRecord,
    DocumentMetadataRecord,
    OrganizationUsageRecord,
    gen_id,
    utcnow,
)

# Canonical 6 Tiers + Backward-Compatibility Aliases
TIER_ALIASES = {
    "INSTITUTIONAL": "BUSINESS",
    "CUSTOM": "ENTERPRISE",
}

SUBSCRIPTION_TIERS_CONFIG: Dict[str, Dict[str, Any]] = {
    "FREE": {
        "tier": "FREE",
        "name": "Community Explorer",
        "price_usd": 0.0,
        "price_ngn": 0.0,
        "max_saved_opportunities": 5,
        "max_active_applications": 1,
        "max_documents_per_app": 3,
        "max_team_members": 1,
        "monthly_copilot_credits": 20,
        "features": {
            "can_export_reports": False,
            "can_access_advanced_copilot": False,
            "can_access_team_workspace": False,
            "can_access_custom_integrations": False,
            "priority_support": False,
            "sla_guarantee": False,
        },
        "description": "Essential access to open verified funding catalog and initial readiness diagnostics.",
    },
    "STARTER": {
        "tier": "STARTER",
        "name": "Emerging Founder",
        "price_usd": 19.0,
        "price_ngn": 29000.0,
        "max_saved_opportunities": 25,
        "max_active_applications": 3,
        "max_documents_per_app": 10,
        "max_team_members": 1,
        "monthly_copilot_credits": 100,
        "features": {
            "can_export_reports": True,
            "can_access_advanced_copilot": False,
            "can_access_team_workspace": False,
            "can_access_custom_integrations": False,
            "priority_support": False,
            "sla_guarantee": False,
        },
        "description": "Ideal for early-stage ventures actively pursuing grant and angel funding.",
    },
    "GROWTH": {
        "tier": "GROWTH",
        "name": "Scaling Venture",
        "price_usd": 49.0,
        "price_ngn": 75000.0,
        "max_saved_opportunities": 100,
        "max_active_applications": 15,
        "max_documents_per_app": 25,
        "max_team_members": 3,
        "monthly_copilot_credits": 500,
        "features": {
            "can_export_reports": True,
            "can_access_advanced_copilot": True,
            "can_access_team_workspace": True,
            "can_access_custom_integrations": False,
            "priority_support": True,
            "sla_guarantee": False,
        },
        "description": "Full AI copilot assistance, team collaboration, and expanded application pipelines.",
    },
    "PRO": {
        "tier": "PRO",
        "name": "Institutional Scale",
        "price_usd": 99.0,
        "price_ngn": 150000.0,
        "max_saved_opportunities": 500,
        "max_active_applications": 50,
        "max_documents_per_app": 100,
        "max_team_members": 5,
        "monthly_copilot_credits": 2000,
        "features": {
            "can_export_reports": True,
            "can_access_advanced_copilot": True,
            "can_access_team_workspace": True,
            "can_access_custom_integrations": False,
            "priority_support": True,
            "sla_guarantee": False,
        },
        "description": "Comprehensive institutional funding discovery, large-scale pipelines, and priority support.",
    },
    "BUSINESS": {
        "tier": "BUSINESS",
        "name": "Venture Studio & Fund",
        "price_usd": 249.0,
        "price_ngn": 380000.0,
        "max_saved_opportunities": 999999,
        "max_active_applications": 999999,
        "max_documents_per_app": 999999,
        "max_team_members": 25,
        "monthly_copilot_credits": 10000,
        "features": {
            "can_export_reports": True,
            "can_access_advanced_copilot": True,
            "can_access_team_workspace": True,
            "can_access_custom_integrations": True,
            "priority_support": True,
            "sla_guarantee": True,
        },
        "description": "For accelerators, studios, and holding entities managing multi-company portfolios.",
    },
    "ENTERPRISE": {
        "tier": "ENTERPRISE",
        "name": "Sovereign & DFI Enterprise",
        "price_usd": 0.0,  # Custom billing
        "price_ngn": 0.0,
        "max_saved_opportunities": 999999,
        "max_active_applications": 999999,
        "max_documents_per_app": 999999,
        "max_team_members": 999999,
        "monthly_copilot_credits": 50000,
        "features": {
            "can_export_reports": True,
            "can_access_advanced_copilot": True,
            "can_access_team_workspace": True,
            "can_access_custom_integrations": True,
            "priority_support": True,
            "sla_guarantee": True,
        },
        "description": "Bespoke deployments, sovereign data residency, custom API quotas, and dedicated directors.",
    },
}

# Alias mapping for backward compatibility with existing tests
SUBSCRIPTION_TIERS_CONFIG["INSTITUTIONAL"] = SUBSCRIPTION_TIERS_CONFIG["BUSINESS"]
SUBSCRIPTION_TIERS_CONFIG["CUSTOM"] = SUBSCRIPTION_TIERS_CONFIG["ENTERPRISE"]


def normalize_tier_name(tier_name: str) -> str:
    cleaned = (tier_name or "FREE").strip().upper()
    return TIER_ALIASES.get(cleaned, cleaned)


def get_current_billing_cycle() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def get_tenant_tier(db: Session, org_id: str) -> str:
    sub = db.execute(
        select(SubscriptionRecord).where(SubscriptionRecord.organization_id == org_id)
    ).scalar_one_or_none()
    if not sub or sub.status != "ACTIVE":
        return "FREE"
    return normalize_tier_name(sub.tier)


def get_or_create_usage(db: Session, org_id: str) -> OrganizationUsageRecord:
    cycle = get_current_billing_cycle()
    usage = db.execute(
        select(OrganizationUsageRecord).where(
            OrganizationUsageRecord.organization_id == org_id,
            OrganizationUsageRecord.billing_cycle == cycle,
        )
    ).scalar_one_or_none()

    if not usage:
        usage = OrganizationUsageRecord(
            usage_id=gen_id("usg"),
            organization_id=org_id,
            billing_cycle=cycle,
            copilot_prompts_used=0,
            copilot_tokens_used=0,
            eligibility_evaluations_used=0,
            custom_quotas={},
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def get_tenant_entitlements_and_usage(db: Session, org_id: str) -> Dict[str, Any]:
    tier_name = get_tenant_tier(db, org_id)
    tier_config = SUBSCRIPTION_TIERS_CONFIG.get(tier_name, SUBSCRIPTION_TIERS_CONFIG["FREE"])
    usage = get_or_create_usage(db, org_id)

    # Count saved opportunities
    saved_count = db.execute(
        select(func.count(SavedOpportunityRecord.saved_id)).where(
            SavedOpportunityRecord.organization_id == org_id
        )
    ).scalar() or 0

    # Count active applications
    active_apps_count = db.execute(
        select(func.count(ApplicationRecord.application_id)).where(
            ApplicationRecord.organization_id == org_id,
            ApplicationRecord.status.notin_(["ARCHIVED", "REJECTED"]),
        )
    ).scalar() or 0

    # Count documents
    total_docs_count = db.execute(
        select(func.count(DocumentMetadataRecord.doc_id)).where(
            DocumentMetadataRecord.organization_id == org_id,
            DocumentMetadataRecord.deleted_at.is_(None),
        )
    ).scalar() or 0

    copilot_credits_limit = tier_config["monthly_copilot_credits"]
    copilot_credits_used = usage.copilot_prompts_used
    copilot_credits_remaining = max(0, copilot_credits_limit - copilot_credits_used)

    return {
        "organization_id": org_id,
        "tier": tier_config["tier"],
        "tier_name": tier_config["name"],
        "price_usd": tier_config["price_usd"],
        "price_ngn": tier_config["price_ngn"],
        "billing_cycle": usage.billing_cycle,
        "quotas": {
            "saved_opportunities": {
                "used": saved_count,
                "limit": tier_config["max_saved_opportunities"],
                "remaining": max(0, tier_config["max_saved_opportunities"] - saved_count),
                "unlimited": tier_config["max_saved_opportunities"] >= 999999,
            },
            "active_applications": {
                "used": active_apps_count,
                "limit": tier_config["max_active_applications"],
                "remaining": max(0, tier_config["max_active_applications"] - active_apps_count),
                "unlimited": tier_config["max_active_applications"] >= 999999,
            },
            "documents_per_app": {
                "limit": tier_config["max_documents_per_app"],
                "total_documents": total_docs_count,
                "unlimited": tier_config["max_documents_per_app"] >= 999999,
            },
            "team_members": {
                "limit": tier_config["max_team_members"],
                "unlimited": tier_config["max_team_members"] >= 999999,
            },
            "copilot_credits": {
                "used": copilot_credits_used,
                "limit": copilot_credits_limit,
                "remaining": copilot_credits_remaining,
                "tokens_used": usage.copilot_tokens_used,
            },
        },
        "features": tier_config["features"],
    }


def check_can_save_opportunity(db: Session, org_id: str):
    tier_name = get_tenant_tier(db, org_id)
    tier_config = SUBSCRIPTION_TIERS_CONFIG.get(tier_name, SUBSCRIPTION_TIERS_CONFIG["FREE"])
    limit = tier_config["max_saved_opportunities"]

    if limit >= 999999:
        return

    saved_count = db.execute(
        select(func.count(SavedOpportunityRecord.saved_id)).where(
            SavedOpportunityRecord.organization_id == org_id
        )
    ).scalar() or 0

    if saved_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Saved opportunities limit reached ({saved_count}/{limit}) for your "
                f"'{tier_config['name']}' plan. Please upgrade to save more opportunities."
            ),
        )


def check_can_create_application(db: Session, org_id: str):
    tier_name = get_tenant_tier(db, org_id)
    tier_config = SUBSCRIPTION_TIERS_CONFIG.get(tier_name, SUBSCRIPTION_TIERS_CONFIG["FREE"])
    limit = tier_config["max_active_applications"]

    if limit >= 999999:
        return

    active_count = db.execute(
        select(func.count(ApplicationRecord.application_id)).where(
            ApplicationRecord.organization_id == org_id,
            ApplicationRecord.status.notin_(["ARCHIVED", "REJECTED"]),
        )
    ).scalar() or 0

    if active_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Active application workspaces limit reached ({active_count}/{limit}) on "
                f"'{tier_config['name']}' plan. Upgrade your plan to manage more pipelines simultaneously."
            ),
        )


def check_can_upload_document(db: Session, org_id: str, application_id: Optional[str] = None):
    tier_name = get_tenant_tier(db, org_id)
    tier_config = SUBSCRIPTION_TIERS_CONFIG.get(tier_name, SUBSCRIPTION_TIERS_CONFIG["FREE"])
    limit = tier_config["max_documents_per_app"]

    if limit >= 999999:
        return

    if application_id:
        doc_count = db.execute(
            select(func.count(DocumentMetadataRecord.doc_id)).where(
                DocumentMetadataRecord.organization_id == org_id,
                DocumentMetadataRecord.application_id == application_id,
                DocumentMetadataRecord.deleted_at.is_(None),
            )
        ).scalar() or 0

        if doc_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Document limit reached ({doc_count}/{limit}) for this application workspace "
                    f"under '{tier_config['name']}' plan. Upgrade to upload more supporting documentation."
                ),
            )


def check_can_use_copilot(db: Session, org_id: str, required_credits: int = 1):
    tier_name = get_tenant_tier(db, org_id)
    tier_config = SUBSCRIPTION_TIERS_CONFIG.get(tier_name, SUBSCRIPTION_TIERS_CONFIG["FREE"])
    limit = tier_config["monthly_copilot_credits"]

    usage = get_or_create_usage(db, org_id)
    if (usage.copilot_prompts_used + required_credits) > limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly CARAVAN Copilot prompt credits exhausted ({usage.copilot_prompts_used}/{limit}). "
                f"Upgrade from '{tier_config['name']}' to a higher tier to continue consulting the AI Funding Copilot."
            ),
        )


def consume_copilot_credits(db: Session, org_id: str, credits: int = 1, tokens: int = 0):
    usage = get_or_create_usage(db, org_id)
    usage.copilot_prompts_used += credits
    usage.copilot_tokens_used += tokens
    usage.updated_at = utcnow()
    db.commit()

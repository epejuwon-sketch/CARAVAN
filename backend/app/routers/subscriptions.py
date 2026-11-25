"""CARAVAN Standalone Platform — Subscriptions & Payment Webhook Routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, get_current_principal
from app.services.payment_service import (
    get_pricing_tiers,
    get_organization_subscription,
    process_payment_webhook,
)

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions & Billing"])


@router.get("/tiers")
@router.get("/pricing")
def api_get_tiers():
    return get_pricing_tiers()


@router.get("/current")
def api_get_current_subscription(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return get_organization_subscription(db, org_id=principal.organization_id)


@router.post("/webhook/{provider}")
async def api_payment_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
    x_flutterwave_signature: Optional[str] = Header(None, alias="verif-hash"),
    x_paystack_signature: Optional[str] = Header(None, alias="x-paystack-signature"),
):
    payload = await request.json()
    sig = x_flutterwave_signature or x_paystack_signature
    return process_payment_webhook(
        db,
        provider=provider,
        payload=payload,
        signature_header=sig,
    )

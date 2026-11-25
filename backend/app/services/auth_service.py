"""CARAVAN Standalone Platform — Authentication & User Management Service."""

from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password, create_access_token
from app.db.models import UserRecord, OrganizationRecord, SubscriptionRecord, AuditLogRecord, gen_id


def register_customer(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    org_name: str,
    entity_type: str = "STARTUP",
    country: str = "Nigeria",
    state_location: str = "Abuja (FCT)",
    sector: str = "Technology",
    stage: str = "SEED",
) -> dict:
    email_clean = email.strip().lower()
    existing = db.execute(select(UserRecord).where(UserRecord.email == email_clean)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    org_id = gen_id("org")
    org = OrganizationRecord(
        org_id=org_id,
        name=org_name.strip(),
        entity_type=entity_type,
        country=country,
        state_location=state_location,
        sector=sector,
        stage=stage,
    )
    db.add(org)

    user_id = gen_id("usr")
    user = UserRecord(
        user_id=user_id,
        organization_id=org_id,
        email=email_clean,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role="CUSTOMER",
    )
    db.add(user)

    # Initialize Free tier subscription
    sub = SubscriptionRecord(
        subscription_id=gen_id("sub"),
        organization_id=org_id,
        tier="FREE",
        price_usd_monthly=0.0,
        billing_provider="MANUAL",
        status="ACTIVE",
    )
    db.add(sub)

    # Audit log
    audit = AuditLogRecord(
        actor=email_clean,
        action="USER_REGISTERED",
        resource=f"user:{user_id}",
        details={"org_name": org_name, "country": country},
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user_id, "org_id": org_id, "email": email_clean, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization_id": org_id,
            "organization_name": org_name,
        },
    }


def authenticate_user(db: Session, email: str, password: str) -> dict:
    email_clean = email.strip().lower()
    user = db.execute(select(UserRecord).where(UserRecord.email == email_clean)).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact CARAVAN support.",
        )

    org = None
    if user.organization_id:
        try:
            org = db.execute(select(OrganizationRecord).where(OrganizationRecord.org_id == user.organization_id)).scalar_one_or_none()
        except Exception as org_err:
            import logging
            logging.getLogger("caravan").warning("Failed to load organization %s during login: %s", user.organization_id, org_err)

    try:
        audit = AuditLogRecord(
            actor=email_clean,
            action="USER_LOGIN",
            resource=f"user:{user.user_id}",
            details={"ip": "client"},
        )
        db.add(audit)
        db.commit()
    except Exception as audit_err:
        db.rollback()
        import logging
        logging.getLogger("caravan").warning("Could not persist login audit log: %s", audit_err)

    token = create_access_token({"sub": user.user_id, "org_id": user.organization_id, "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization_id": user.organization_id,
            "organization_name": org.name if org else "Personal Workspace",
        },
    }

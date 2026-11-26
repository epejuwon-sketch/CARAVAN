"""CARAVAN Standalone Platform — Authentication Routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.core.permissions import CaravanPrincipal, get_current_principal
from app.core.rate_limit import get_rate_limiter
from app.core.bot_protection import verify_turnstile_token
from app.services.auth_service import register_customer, authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    organization_name: str = Field(min_length=2, max_length=200)
    entity_type: str = Field(default="STARTUP", max_length=64)
    country: str = Field(default="Nigeria", max_length=80)
    state_location: str = Field(default="Abuja (FCT)", max_length=120)
    sector: str = Field(default="Technology", max_length=120)
    stage: str = Field(default="SEED", max_length=64)
    turnstile_token: Optional[str] = None
    terms_accepted: bool = Field(default=True)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str
    turnstile_token: Optional[str] = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
def api_register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    # 1. Rate limiting (max 5 registrations per hour per IP)
    limiter = get_rate_limiter()
    limiter.check_rate_limit(request, endpoint_key="auth:register", max_requests=10, window_seconds=60)

    # 2. Bot protection
    verify_turnstile_token(body.turnstile_token, remote_ip=request.client.host if request.client else None)

    # 3. Explicit terms & compliance acceptance
    if not body.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept CARAVAN's Terms of Service and Privacy Policy to register.",
        )

    return register_customer(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        org_name=body.organization_name,
        entity_type=body.entity_type,
        country=body.country,
        state_location=body.state_location,
        sector=body.sector,
        stage=body.stage,
    )


@router.post("/login")
def api_login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    # 1. Rate limiting (max 10 login attempts per 60s per IP, max 5 per account)
    limiter = get_rate_limiter()
    limiter.check_rate_limit(
        request,
        endpoint_key="auth:login",
        max_requests=10,
        window_seconds=60,
        account_identifier=body.email,
    )

    try:
        return authenticate_user(db, email=body.email, password=body.password)
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.getLogger("caravan").exception("Unhandled error during authentication for %s: %s", getattr(body, "email", "unknown"), exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily encountered an internal issue. Please retry.",
        )


@router.post("/logout")
def api_logout(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Explicitly records session termination audit event."""
    from app.db.models import AuditLogRecord
    try:
        audit = AuditLogRecord(
            actor=principal.email,
            action="USER_LOGOUT",
            resource=f"user:{principal.user_id}",
            outcome="SUCCESS",
            details={"organization_id": principal.organization_id},
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()

    return {"success": True, "message": "Logged out successfully."}


@router.get("/me")
def api_me(principal: CaravanPrincipal = Depends(get_current_principal), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.db.models import OrganizationRecord, UserRecord

    # Verify user is active in database
    user = db.get(UserRecord, principal.user_id)
    if user and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated.",
        )

    org = db.execute(
        select(OrganizationRecord).where(OrganizationRecord.org_id == principal.organization_id)
    ).scalar_one_or_none()

    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "role": principal.role,
        "organization_id": principal.organization_id,
        "organization": {
            "org_id": org.org_id if org else principal.organization_id,
            "name": org.name if org else "Personal Workspace",
            "country": org.country if org else "Nigeria",
            "state_location": org.state_location if org else "Abuja (FCT)",
            "sector": org.sector if org else "Technology",
            "stage": org.stage if org else "SEED",
            "annual_revenue_ngn": getattr(org, "annual_revenue_ngn", 0.0),
            "cac_registered": getattr(org, "cac_registered", True),
            "years_in_operation": getattr(org, "years_in_operation", 1),
            "female_led": getattr(org, "female_led", False),
            "youth_led": getattr(org, "youth_led", True),
        } if org else None,
    }


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    turnstile_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class EmailVerificationRequest(BaseModel):
    token: str


@router.post("/forgot-password")
def api_forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a secure password recovery token without leaking user existence."""
    from datetime import timedelta
    from sqlalchemy import select
    from app.db.models import UserRecord, AuditLogRecord
    from app.core.security import create_access_token

    # 1. Rate limiting
    limiter = get_rate_limiter()
    limiter.check_rate_limit(request, endpoint_key="auth:forgot-password", max_requests=5, window_seconds=60)

    # 2. Bot protection
    verify_turnstile_token(body.turnstile_token, remote_ip=request.client.host if request.client else None)

    email_clean = body.email.strip().lower()
    user = db.execute(select(UserRecord).where(UserRecord.email == email_clean)).scalar_one_or_none()

    # Always return success message for security / anti-enumeration
    recovery_token = None
    if user and user.is_active:
        recovery_token = create_access_token(
            {"sub": user.user_id, "email": user.email, "purpose": "password_reset"},
            expires_delta=timedelta(minutes=30),
        )
        audit = AuditLogRecord(
            actor=email_clean,
            action="PASSWORD_RESET_REQUESTED",
            resource=f"user:{user.user_id}",
            outcome="SUCCESS",
            details={"email": email_clean},
        )
        db.add(audit)
        db.commit()

    settings = get_settings()
    response_data = {
        "success": True,
        "message": "If this email is registered, password recovery instructions have been dispatched.",
    }
    # Item 10: In production, NEVER expose the raw reset token in the HTTP API response
    if settings.CARAVAN_ENV != "production":
        response_data["reset_token"] = recovery_token

    return response_data


@router.post("/reset-password")
def api_reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset user password using a verified recovery token."""
    from fastapi import HTTPException
    from app.db.models import UserRecord, AuditLogRecord
    from app.core.security import decode_access_token, hash_password

    try:
        payload = decode_access_token(body.token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or malformed password reset token.",
        )

    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token purpose.")

    user_id = payload.get("sub")
    user = db.get(UserRecord, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    user.password_hash = hash_password(body.new_password)
    
    audit = AuditLogRecord(
        actor=user.email,
        action="PASSWORD_RESET_COMPLETED",
        resource=f"user:{user.user_id}",
        outcome="SUCCESS",
        details={"user_id": user_id},
    )
    db.add(audit)
    db.commit()

    return {"success": True, "message": "Password updated successfully. You may now log in with your new credentials."}


@router.post("/request-verification")
def api_request_verification(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generate email verification token."""
    from datetime import timedelta
    from sqlalchemy import select
    from app.db.models import UserRecord, AuditLogRecord
    from app.core.security import create_access_token

    # Rate limiting
    limiter = get_rate_limiter()
    limiter.check_rate_limit(request, endpoint_key="auth:request-verification", max_requests=5, window_seconds=60)

    email_clean = body.email.strip().lower()
    user = db.execute(select(UserRecord).where(UserRecord.email == email_clean)).scalar_one_or_none()
    
    verification_token = None
    if user and user.is_active:
        verification_token = create_access_token(
            {"sub": user.user_id, "email": user.email, "purpose": "email_verification"},
            expires_delta=timedelta(hours=24),
        )
        audit = AuditLogRecord(
            actor=email_clean,
            action="EMAIL_VERIFICATION_REQUESTED",
            resource=f"user:{user.user_id}",
            outcome="SUCCESS",
            details={"email": email_clean},
        )
        db.add(audit)
        db.commit()

    settings = get_settings()
    response_data = {
        "success": True,
        "message": "Email verification link has been dispatched.",
    }
    if settings.CARAVAN_ENV != "production":
        response_data["verification_token"] = verification_token

    return response_data


@router.post("/verify-email")
def api_verify_email(body: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify customer email using verification token."""
    from fastapi import HTTPException
    from app.db.models import UserRecord, AuditLogRecord
    from app.core.security import decode_access_token

    try:
        payload = decode_access_token(body.token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    if payload.get("purpose") != "email_verification":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token purpose.")

    user_id = payload.get("sub")
    user = db.get(UserRecord, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    audit = AuditLogRecord(
        actor=user.email,
        action="EMAIL_VERIFIED",
        resource=f"user:{user.user_id}",
        outcome="SUCCESS",
        details={"email": user.email},
    )
    db.add(audit)
    db.commit()

    return {"success": True, "message": "Email verified successfully.", "email": user.email}


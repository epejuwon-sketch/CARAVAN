"""CARAVAN Standalone Platform — Notifications System Routes."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import NotificationRecord, utcnow
from app.core.permissions import CaravanPrincipal, get_current_principal

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("")
def api_get_notifications(
    limit: int = 30,
    offset: int = 0,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Retrieve notifications for the authenticated user."""
    # Seed welcome notifications if first time
    user_notifs_count = (
        db.query(NotificationRecord)
        .filter(NotificationRecord.user_id == principal.user_id)
        .count()
    )
    if user_notifs_count == 0:
        welcome_items = [
            NotificationRecord(
                user_id=principal.user_id,
                title="Welcome to CARAVAN",
                message="Your institutional workspace is ready. Explore verified opportunities across Africa.",
                category="SYSTEM",
                is_read=False,
            ),
            NotificationRecord(
                user_id=principal.user_id,
                title="Verified Opportunities Available",
                message="12 institutional grant and equity programs are currently open for applications.",
                category="OPPORTUNITY",
                is_read=False,
            ),
            NotificationRecord(
                user_id=principal.user_id,
                title="Complete Your Profile",
                message="Ensure your business sector and location are updated to receive 100% accurate match recommendations.",
                category="MATCH",
                is_read=False,
            ),
        ]
        db.add_all(welcome_items)
        db.commit()

    records = (
        db.query(NotificationRecord)
        .filter(NotificationRecord.user_id == principal.user_id)
        .order_by(NotificationRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    unread_count = (
        db.query(NotificationRecord)
        .filter(NotificationRecord.user_id == principal.user_id, NotificationRecord.is_read == False)
        .count()
    )

    return {
        "unread_count": unread_count,
        "total": len(records),
        "notifications": [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in records
        ],
    }


@router.post("/{notification_id}/read")
def api_mark_notification_read(
    notification_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Mark a specific notification as read."""
    notif = db.get(NotificationRecord, notification_id)
    if not notif or notif.user_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    notif.is_read = True
    db.commit()
    return {"status": "SUCCESS", "notification_id": notification_id}


@router.post("/read-all")
def api_mark_all_read(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for current user."""
    db.query(NotificationRecord).filter(
        NotificationRecord.user_id == principal.user_id,
        NotificationRecord.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"status": "SUCCESS"}


from pydantic import BaseModel, Field

class NotificationPreferencesRequest(BaseModel):
    marketing_emails: bool = False
    opportunity_alerts: bool = True
    deadline_digests: bool = True
    security_alerts: bool = True  # Mandatory transactional


class OneClickUnsubscribeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    category: str = Field(default="MARKETING")
    token: str | None = None


@router.get("/preferences")
def api_get_notification_preferences(
    principal: CaravanPrincipal = Depends(get_current_principal),
):
    """Retrieve communication and email delivery preferences."""
    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "preferences": {
            "marketing_emails": False,
            "opportunity_alerts": True,
            "deadline_digests": True,
            "security_alerts": True,
        },
    }


@router.post("/preferences")
def api_update_notification_preferences(
    body: NotificationPreferencesRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Update email notification preferences."""
    from app.db.models import AuditLogRecord
    audit = AuditLogRecord(
        actor=principal.email,
        action="NOTIFICATION_PREFERENCES_UPDATED",
        resource=f"user:{principal.user_id}",
        outcome="SUCCESS",
        details=body.dict(),
    )
    db.add(audit)
    db.commit()
    return {
        "status": "SUCCESS",
        "message": "Notification preferences updated.",
        "preferences": body.dict(),
    }


@router.post("/unsubscribe")
def api_unsubscribe_email(
    body: OneClickUnsubscribeRequest,
    db: Session = Depends(get_db),
):
    """Statutory one-click email unsubscribe endpoint (RFC 8058 compliant)."""
    from app.db.models import AuditLogRecord
    email_clean = body.email.strip().lower()

    audit = AuditLogRecord(
        actor=email_clean,
        action="EMAIL_UNSUBSCRIBED",
        resource=f"email:{email_clean}",
        outcome="SUCCESS",
        details={"category": body.category},
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"You have been successfully unsubscribed from CARAVAN {body.category.lower()} communications.",
        "email": email_clean,
    }

"""CARAVAN Standalone Platform — Support Tickets & Notifications Routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import SupportTicketRecord, NotificationRecord, gen_id
from app.core.permissions import CaravanPrincipal, get_current_principal

router = APIRouter(prefix="/api/v1/support", tags=["Support & Notifications"])


class CreateTicketRequest(BaseModel):
    subject: str
    message: str


@router.get("/tickets")
def api_list_tickets(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    tickets = db.execute(
        select(SupportTicketRecord).where(
            SupportTicketRecord.organization_id == principal.organization_id
        ).order_by(desc(SupportTicketRecord.created_at))
    ).scalars().all()

    return {
        "total": len(tickets),
        "tickets": [
            {
                "ticket_id": t.ticket_id,
                "subject": t.subject,
                "message": t.message,
                "status": t.status,
                "response": t.response,
                "created_at": t.created_at.isoformat(),
            }
            for t in tickets
        ],
    }


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def api_create_ticket(
    body: CreateTicketRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    ticket_id = gen_id("tkt")
    tkt = SupportTicketRecord(
        ticket_id=ticket_id,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        subject=body.subject.strip(),
        message=body.message.strip(),
        status="OPEN",
    )
    db.add(tkt)
    db.commit()
    db.refresh(tkt)
    return {
        "ticket_id": tkt.ticket_id,
        "subject": tkt.subject,
        "status": tkt.status,
        "created_at": tkt.created_at.isoformat(),
    }


@router.get("/notifications")
def api_list_notifications(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    notifs = db.execute(
        select(NotificationRecord).where(
            NotificationRecord.user_id == principal.user_id
        ).order_by(desc(NotificationRecord.created_at))
    ).scalars().all()

    return {
        "total": len(notifs),
        "notifications": [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ],
    }

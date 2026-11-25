"""CARAVAN Standalone Platform — Application Preparation Workspace & Pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models import (
    ApplicationRecord,
    FundingOpportunityRecord,
    DocumentMetadataRecord,
    AuditLogRecord,
    gen_id,
)

APPLICATION_STATUSES = ["DRAFTING", "DOCS_COLLECTING", "REVIEW", "SUBMITTED", "AWARDED", "REJECTED"]


def list_applications(db: Session, org_id: str) -> List[dict]:
    apps = db.execute(
        select(ApplicationRecord).where(ApplicationRecord.organization_id == org_id).order_by(desc(ApplicationRecord.updated_at))
    ).scalars().all()

    results = []
    for a in apps:
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == a.opportunity_id)
        ).scalar_one_or_none()
        results.append({
            "application_id": a.application_id,
            "organization_id": a.organization_id,
            "opportunity_id": a.opportunity_id,
            "opportunity_title": opp.title if opp else "Unknown Opportunity",
            "provider": opp.provider if opp else "Unknown Provider",
            "funding_type": opp.funding_type if opp else "GRANT",
            "status": a.status,
            "checklist_progress": a.checklist_progress,
            "deadline_at": a.deadline_at.isoformat() if a.deadline_at else None,
            "notes": a.notes,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        })
    return results


def get_application_workspace(db: Session, org_id: str, application_id: str) -> dict:
    app = db.execute(
        select(ApplicationRecord).where(
            ApplicationRecord.application_id == application_id,
            ApplicationRecord.organization_id == org_id,
        )
    ).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found.")

    opp = db.execute(
        select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == app.opportunity_id)
    ).scalar_one_or_none()

    docs = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.application_id == application_id,
            DocumentMetadataRecord.organization_id == org_id,
        )
    ).scalars().all()

    return {
        "application_id": app.application_id,
        "organization_id": app.organization_id,
        "opportunity_id": app.opportunity_id,
        "opportunity_title": opp.title if opp else "Unknown Opportunity",
        "provider": opp.provider if opp else "Unknown Provider",
        "funding_type": opp.funding_type if opp else "GRANT",
        "status": app.status,
        "checklist_progress": app.checklist_progress,
        "deadline_at": app.deadline_at.isoformat() if app.deadline_at else None,
        "notes": app.notes,
        "documents": [
            {
                "doc_id": d.doc_id,
                "name": d.name,
                "doc_type": d.doc_type,
                "file_size_bytes": d.file_size_bytes,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in docs
        ],
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


def create_application_workspace(db: Session, org_id: str, opportunity_id: str, notes: str = "") -> dict:
    opp = db.execute(
        select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
    ).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funding opportunity not found.")

    existing = db.execute(
        select(ApplicationRecord).where(
            ApplicationRecord.organization_id == org_id,
            ApplicationRecord.opportunity_id == opportunity_id,
        )
    ).scalar_one_or_none()
    if existing:
        return {
            "application_id": existing.application_id,
            "status": existing.status,
            "already_existed": True,
        }

    # Initialize checklist from opportunity requirements
    reqs = opp.application_requirements or [
        "Executive Summary & Mission",
        "Pitch Deck & Presentation",
        "Financial Forecast & 12-Month Budget",
        "Certificate of Incorporation / Registration",
    ]
    checklist = [{"item": r, "completed": False} for r in reqs]

    app_id = gen_id("app")
    app_rec = ApplicationRecord(
        application_id=app_id,
        organization_id=org_id,
        opportunity_id=opportunity_id,
        status="DRAFTING",
        checklist_progress=checklist,
        deadline_at=opp.deadline_at,
        notes=notes,
    )
    db.add(app_rec)

    audit = AuditLogRecord(
        actor=f"org:{org_id}",
        action="APPLICATION_CREATED",
        resource=f"application:{app_id}",
        details={"opportunity_id": opportunity_id, "title": opp.title},
    )
    db.add(audit)
    db.commit()
    db.refresh(app_rec)

    return {
        "application_id": app_rec.application_id,
        "opportunity_id": opportunity_id,
        "status": app_rec.status,
        "checklist_progress": app_rec.checklist_progress,
        "deadline_at": app_rec.deadline_at.isoformat() if app_rec.deadline_at else None,
    }


def update_application_status(
    db: Session,
    org_id: str,
    application_id: str,
    status_update: Optional[str] = None,
    checklist_update: Optional[List[dict]] = None,
    notes_update: Optional[str] = None,
) -> dict:
    app_rec = db.execute(
        select(ApplicationRecord).where(
            ApplicationRecord.application_id == application_id,
            ApplicationRecord.organization_id == org_id,
        )
    ).scalar_one_or_none()
    if not app_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found.")

    if status_update:
        status_clean = status_update.upper()
        if status_clean not in APPLICATION_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status '{status_update}'.")
        app_rec.status = status_clean

    if checklist_update is not None:
        app_rec.checklist_progress = checklist_update

    if notes_update is not None:
        app_rec.notes = notes_update

    app_rec.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "application_id": app_rec.application_id,
        "status": app_rec.status,
        "checklist_progress": app_rec.checklist_progress,
        "notes": app_rec.notes,
        "updated_at": app_rec.updated_at.isoformat(),
    }


def add_document_metadata(
    db: Session,
    org_id: str,
    application_id: Optional[str],
    name: str,
    doc_type: str = "PITCH_DECK",
    file_size_bytes: int = 1024,
) -> dict:
    doc_id = gen_id("doc")
    doc = DocumentMetadataRecord(
        doc_id=doc_id,
        organization_id=org_id,
        application_id=application_id,
        name=name.strip(),
        doc_type=doc_type.upper(),
        file_size_bytes=file_size_bytes,
    )
    db.add(doc)
    db.commit()
    return {
        "doc_id": doc.doc_id,
        "organization_id": doc.organization_id,
        "application_id": doc.application_id,
        "name": doc.name,
        "doc_type": doc.doc_type,
        "file_size_bytes": doc.file_size_bytes,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }

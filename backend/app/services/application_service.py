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
from app.services.malware_scanner import scan_file_bytes
from app.services.storage_service import get_storage_service

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
    # 1. Tenant ownership validation for linked application
    if application_id:
        app_check = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not app_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found.")

    # 2. Filename sanitization
    clean_name = name.strip().replace("\0", "").replace("../", "").replace("..\\", "")
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document filename.")

    # 3. Document type validation
    valid_types = {
        "PITCH_DECK",
        "FINANCIALS",
        "CERTIFICATE",
        "TAX_CLEARANCE",
        "AUDITED_ACCOUNTS",
        "BUSINESS_PLAN",
        "OTHER",
    }
    clean_type = doc_type.upper().strip()
    if clean_type not in valid_types:
        clean_type = "OTHER"

    # 4. File size limit enforcement (25 MB max)
    MAX_FILE_BYTES = 25 * 1024 * 1024
    if file_size_bytes <= 0 or file_size_bytes > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size must be between 1 byte and 25 MB ({MAX_FILE_BYTES} bytes).",
        )

    doc_id = gen_id("doc")
    doc = DocumentMetadataRecord(
        doc_id=doc_id,
        organization_id=org_id,
        application_id=application_id,
        name=clean_name[:255],
        doc_type=clean_type,
        file_size_bytes=file_size_bytes,
        scan_status="AVAILABLE",
        scan_details={"details": "Direct metadata registration."},
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
        "scan_status": doc.scan_status,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


def upload_document_binary(
    db: Session,
    org_id: str,
    application_id: Optional[str],
    filename: str,
    file_bytes: bytes,
    doc_type: str = "PITCH_DECK",
    actor: str = "anonymous",
) -> dict:
    """Validate, scan for malware, persist in private tenant storage, and record document."""
    # 1. Tenant ownership validation
    if application_id:
        app_check = db.execute(
            select(ApplicationRecord).where(
                ApplicationRecord.application_id == application_id,
                ApplicationRecord.organization_id == org_id,
            )
        ).scalar_one_or_none()
        if not app_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application workspace not found.")

    # 2. Filename sanitization
    clean_name = filename.strip().replace("\0", "").replace("../", "").replace("..\\", "")
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document filename.")

    # 3. File extension & size check
    MAX_FILE_BYTES = 25 * 1024 * 1024
    if len(file_bytes) == 0 or len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size must be between 1 byte and 25 MB ({MAX_FILE_BYTES} bytes).",
        )

    allowed_exts = {"pdf", "png", "jpg", "jpeg", "docx", "xlsx"}
    ext = clean_name.rsplit(".", 1)[-1].lower() if "." in clean_name else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not permitted. Allowed: {', '.join(sorted(allowed_exts))}",
        )

    # 4. Anti-malware and magic header security inspection
    scan_report = scan_file_bytes(file_bytes, clean_name)
    storage = get_storage_service()
    doc_id = gen_id("doc")

    if not scan_report.is_clean:
        # Quarantine file in isolated storage and record audit event
        storage_res = storage.store_document(org_id, doc_id, file_bytes, quarantined=True)
        doc = DocumentMetadataRecord(
            doc_id=doc_id,
            organization_id=org_id,
            application_id=application_id,
            name=clean_name[:255],
            doc_type=doc_type.upper().strip(),
            file_size_bytes=len(file_bytes),
            storage_path=storage_res.storage_path,
            content_type=f"application/{ext}",
            scan_status="QUARANTINED",
            scan_details=scan_report.to_dict(),
            sha256_hash=storage_res.sha256_hash,
        )
        db.add(doc)
        audit = AuditLogRecord(
            actor=actor,
            action="DOCUMENT_QUARANTINED",
            resource=f"doc:{doc_id}",
            outcome="FLAGGED",
            details=scan_report.to_dict(),
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security scan rejected file: {scan_report.details} Threat: {scan_report.threat_name}",
        )

    # Clean file: Store in private tenant vault
    storage_res = storage.store_document(org_id, doc_id, file_bytes, quarantined=False)
    doc = DocumentMetadataRecord(
        doc_id=doc_id,
        organization_id=org_id,
        application_id=application_id,
        name=clean_name[:255],
        doc_type=doc_type.upper().strip(),
        file_size_bytes=len(file_bytes),
        storage_path=storage_res.storage_path,
        content_type=f"application/{ext}",
        scan_status="AVAILABLE",
        scan_details=scan_report.to_dict(),
        sha256_hash=storage_res.sha256_hash,
    )
    db.add(doc)
    audit = AuditLogRecord(
        actor=actor,
        action="DOCUMENT_UPLOADED",
        resource=f"doc:{doc_id}",
        outcome="SUCCESS",
        details={"name": clean_name, "size": len(file_bytes), "sha256": storage_res.sha256_hash},
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)

    return {
        "doc_id": doc.doc_id,
        "organization_id": doc.organization_id,
        "application_id": doc.application_id,
        "name": doc.name,
        "doc_type": doc.doc_type,
        "file_size_bytes": doc.file_size_bytes,
        "scan_status": doc.scan_status,
        "sha256_hash": doc.sha256_hash,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "download_url": f"/api/v1/applications/{application_id}/documents/{doc.doc_id}/download",
    }


def download_document_binary(db: Session, org_id: str, application_id: str, doc_id: str, actor: str) -> Tuple[bytes, str, str]:
    """Retrieve private document bytes verifying tenant ownership and clean scan status."""
    doc = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.doc_id == doc_id,
            DocumentMetadataRecord.organization_id == org_id,
            DocumentMetadataRecord.application_id == application_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if doc.scan_status == "QUARANTINED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Document is in quarantine due to security threats.",
        )

    storage = get_storage_service()
    content, file_path = storage.retrieve_document(org_id, doc_id)

    audit = AuditLogRecord(
        actor=actor,
        action="DOCUMENT_DOWNLOADED",
        resource=f"doc:{doc_id}",
        outcome="SUCCESS",
        details={"name": doc.name, "size": doc.file_size_bytes},
    )
    db.add(audit)
    db.commit()

    return content, doc.name, doc.content_type


def get_document_download_token(db: Session, org_id: str, application_id: str, doc_id: str) -> dict:
    """Generate scoped temporary signed download token."""
    doc = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.doc_id == doc_id,
            DocumentMetadataRecord.organization_id == org_id,
            DocumentMetadataRecord.application_id == application_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.scan_status == "QUARANTINED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Document is quarantined.")

    storage = get_storage_service()
    token = storage.generate_scoped_download_token(org_id, doc_id, expires_in_seconds=900)
    return {
        "doc_id": doc_id,
        "token": token,
        "expires_in_seconds": 900,
        "stream_url": f"/api/v1/applications/{application_id}/documents/{doc_id}/stream?token={token}",
    }


def delete_document_metadata(db: Session, org_id: str, doc_id: str, actor: str = "org_user") -> dict:
    """Safely delete document metadata and shred physical storage, strictly scoped to the tenant organization."""
    doc = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.doc_id == doc_id,
            DocumentMetadataRecord.organization_id == org_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    storage = get_storage_service()
    storage.delete_document(org_id, doc_id)

    db.delete(doc)
    audit = AuditLogRecord(
        actor=actor,
        action="DOCUMENT_DELETED",
        resource=f"doc:{doc_id}",
        outcome="SUCCESS",
        details={"doc_name": doc.name},
    )
    db.add(audit)
    db.commit()
    return {"status": "DELETED", "doc_id": doc_id}

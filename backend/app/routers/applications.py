"""CARAVAN Standalone Platform — Application Workspace Routes."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Response, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import CaravanPrincipal, get_current_principal
from app.services.application_service import (
    list_applications,
    get_application_workspace,
    create_application_workspace,
    update_application_status,
    add_document_metadata,
    upload_document_binary,
    download_document_binary,
    get_document_download_token,
    delete_document_metadata,
)
from app.services.storage_service import get_storage_service

router = APIRouter(prefix="/api/v1/applications", tags=["Applications"])


class CreateApplicationRequest(BaseModel):
    opportunity_id: str
    notes: Optional[str] = ""


class UpdateApplicationRequest(BaseModel):
    status: Optional[str] = None
    checklist_progress: Optional[List[dict]] = None
    notes: Optional[str] = None


class AddDocumentRequest(BaseModel):
    name: str
    doc_type: str = "PITCH_DECK"
    file_size_bytes: int = 2048


@router.get("")
def api_list_applications(
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    apps = list_applications(db, org_id=principal.organization_id)
    return {"total": len(apps), "applications": apps}


@router.get("/{application_id}")
def api_get_application(
    application_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return get_application_workspace(
        db,
        org_id=principal.organization_id,
        application_id=application_id,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def api_create_application(
    body: CreateApplicationRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return create_application_workspace(
        db,
        org_id=principal.organization_id,
        opportunity_id=body.opportunity_id,
        notes=body.notes or "",
    )


@router.patch("/{application_id}")
@router.put("/{application_id}")
def api_update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return update_application_status(
        db,
        org_id=principal.organization_id,
        application_id=application_id,
        status_update=body.status,
        checklist_update=body.checklist_progress,
        notes_update=body.notes,
    )


@router.post("/{application_id}/documents", status_code=status.HTTP_201_CREATED)
def api_add_document(
    application_id: str,
    body: AddDocumentRequest,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return add_document_metadata(
        db,
        org_id=principal.organization_id,
        application_id=application_id,
        name=body.name,
        doc_type=body.doc_type,
        file_size_bytes=body.file_size_bytes,
    )


@router.post("/{application_id}/documents/upload", status_code=status.HTTP_201_CREATED)
async def api_upload_document(
    application_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form("PITCH_DECK"),
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Secure multipart binary file upload with anti-malware inspection and private vault storage."""
    file_bytes = await file.read()
    return upload_document_binary(
        db=db,
        org_id=principal.organization_id,
        application_id=application_id,
        filename=file.filename or "uploaded_document.bin",
        file_bytes=file_bytes,
        doc_type=doc_type,
        actor=principal.user_id,
    )


@router.get("/{application_id}/documents/{doc_id}/download")
def api_download_document(
    application_id: str,
    doc_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Download private document bytes, enforcing tenant ownership and clean malware scan status."""
    content, filename, content_type = download_document_binary(
        db=db,
        org_id=principal.organization_id,
        application_id=application_id,
        doc_id=doc_id,
        actor=principal.user_id,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "private, no-cache, no-store, must-revalidate",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }
    return Response(content=content, media_type=content_type, headers=headers)


@router.get("/{application_id}/documents/{doc_id}/signed-url")
def api_get_signed_document_url(
    application_id: str,
    doc_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Generate a 15-minute scoped signed download token."""
    return get_document_download_token(
        db=db,
        org_id=principal.organization_id,
        application_id=application_id,
        doc_id=doc_id,
    )


@router.get("/{application_id}/documents/{doc_id}/stream")
def api_stream_signed_document(
    application_id: str,
    doc_id: str,
    token: str = Query(..., description="Short-lived HMAC signed token"),
    db: Session = Depends(get_db),
):
    """Retrieve document via temporary signed token, verifying expiry and signature."""
    from app.db.models import DocumentMetadataRecord
    from sqlalchemy import select

    doc = db.execute(
        select(DocumentMetadataRecord).where(
            DocumentMetadataRecord.doc_id == doc_id,
            DocumentMetadataRecord.application_id == application_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    storage = get_storage_service()
    if not storage.verify_scoped_download_token(doc.organization_id, doc_id, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired download token.")

    if doc.scan_status == "QUARANTINED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Document quarantined.")

    content, _ = storage.retrieve_document(doc.organization_id, doc_id)
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.name}"',
        "Cache-Control": "private, no-cache, no-store, must-revalidate",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=content, media_type=doc.content_type, headers=headers)


@router.delete("/{application_id}/documents/{doc_id}")
def api_delete_document(
    application_id: str,
    doc_id: str,
    principal: CaravanPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return delete_document_metadata(
        db,
        org_id=principal.organization_id,
        doc_id=doc_id,
        actor=principal.user_id,
    )

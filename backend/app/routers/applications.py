"""CARAVAN Standalone Platform — Application Workspace Routes."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, status
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
)

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

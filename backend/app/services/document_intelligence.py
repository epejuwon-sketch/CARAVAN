"""CARAVAN Standalone Platform — Document Intelligence & Verification Engine.

Provides tenant-isolated document classification, entity and text inspection,
document-to-requirement matching, missing document detection, and expiration audits.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentMetadataRecord, FundingOpportunityRecord, OrganizationRecord, utcnow


# Canonical document categories required by institutional funders in Nigeria & Africa
DOCUMENT_TYPES = {
    "CAC_CERTIFICATE": {
        "label": "CAC Certificate of Registration / Incorporation",
        "keywords": ["cac", "certificate", "incorporation", "registration", "status report", "rc", "bn"],
        "expires": False,
    },
    "TAX_CLEARANCE": {
        "label": "Tax Clearance Certificate (TCC / TIN)",
        "keywords": ["tax", "clearance", "tcc", "firs", "tin", "withholding"],
        "expires": True,
        "validity_days": 365,
    },
    "BANK_STATEMENTS": {
        "label": "Certified Corporate Bank Statements (6-12 Months)",
        "keywords": ["bank", "statement", "account", "ebills", "financial", "ledger", "gtbank", "zenith", "access"],
        "expires": True,
        "validity_days": 180,  # Funder standard: not older than 6 months
    },
    "AUDITED_FINANCIALS": {
        "label": "Audited Financial Statements / Management Accounts",
        "keywords": ["audit", "financials", "balance sheet", "p&l", "profit", "loss", "management accounts"],
        "expires": True,
        "validity_days": 365,
    },
    "PITCH_DECK": {
        "label": "Executive Pitch Deck & Business Feasibility Plan",
        "keywords": ["pitch", "deck", "presentation", "business plan", "feasibility", "proposal"],
        "expires": False,
    },
    "REGULATORY_LICENSE": {
        "label": "Industry Regulatory License / Permit (NAFDAC, NEPC, SON, NOGIC)",
        "keywords": ["license", "permit", "nafdac", "nepc", "nogic", "son", "cbn", "sec", "dpr"],
        "expires": True,
        "validity_days": 730,
    },
    "DIRECTOR_ID": {
        "label": "Director / Founder Identification (NIN / International Passport)",
        "keywords": ["passport", "nin", "voters", "identification", "id", "director", "founder"],
        "expires": True,
        "validity_days": 1825,
    },
}


class DocumentIntelligence:
    """Document classification, requirement matching, and compliance validation."""

    @staticmethod
    def classify_document(filename: str, doc_type_hint: Optional[str] = None) -> str:
        """Classify document category using filename heuristic or provided hint."""
        if doc_type_hint and doc_type_hint.upper() in DOCUMENT_TYPES:
            return doc_type_hint.upper()

        fn_lower = filename.lower()
        for dtype, meta in DOCUMENT_TYPES.items():
            for kw in meta["keywords"]:
                if kw in fn_lower:
                    return dtype

        return "PITCH_DECK"

    @staticmethod
    def inspect_document(doc: DocumentMetadataRecord) -> Dict[str, Any]:
        """Inspect document freshness, security scan status, and metadata completeness."""
        now = datetime.now(timezone.utc)
        created_at = getattr(doc, "uploaded_at", None) or getattr(doc, "created_at", None) or now
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        dtype = doc.doc_type or "PITCH_DECK"
        meta = DOCUMENT_TYPES.get(dtype, {"label": dtype, "expires": False})

        is_expired = False
        expiry_date = None
        if meta.get("expires") and meta.get("validity_days"):
            expiry_date = created_at + timedelta(days=meta["validity_days"])
            if now > expiry_date:
                is_expired = True

        return {
            "doc_id": doc.doc_id,
            "name": doc.name,
            "doc_type": dtype,
            "label": meta["label"],
            "file_size_bytes": doc.file_size_bytes,
            "content_type": doc.content_type,
            "scan_status": getattr(doc, "scan_status", "AVAILABLE"),
            "is_expired": is_expired,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "uploaded_at": created_at.isoformat(),
        }

    @staticmethod
    def match_documents_to_requirements(
        db: Session,
        org_id: str,
        opportunity_id: str,
    ) -> Dict[str, Any]:
        """Audit organization documents against opportunity requirements with tenant isolation."""
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
        ).scalar_one_or_none()

        # Retrieve all uploaded documents belonging strictly to this organization
        docs = db.execute(
            select(DocumentMetadataRecord).where(DocumentMetadataRecord.organization_id == org_id)
        ).scalars().all()

        available_inspections = [DocumentIntelligence.inspect_document(d) for d in docs]
        available_types = {d["doc_type"] for d in available_inspections if not d["is_expired"]}

        # Normalize opportunity requirements
        opp_reqs: List[str] = (opp.application_requirements if opp else []) or [
            "CAC Certificate of Incorporation",
            "12 Months Corporate Bank Statements",
            "Tax Clearance Certificate",
            "Executive Pitch Deck & Feasibility Report",
        ]

        matched_items: List[Dict[str, Any]] = []
        missing_items: List[Dict[str, Any]] = []

        for req in opp_reqs:
            req_lower = req.lower()
            matched_doc = None

            for d in available_inspections:
                dtype = d["doc_type"]
                meta = DOCUMENT_TYPES.get(dtype, {"keywords": []})
                # Check keyword match
                if any(kw in req_lower for kw in meta["keywords"]):
                    matched_doc = d
                    break

            if matched_doc:
                matched_items.append({
                    "requirement": req,
                    "satisfied": True,
                    "document": matched_doc,
                })
            else:
                # Suggest document category to upload
                suggested_type = "PITCH_DECK"
                for dt, m in DOCUMENT_TYPES.items():
                    if any(kw in req_lower for kw in m["keywords"]):
                        suggested_type = dt
                        break

                missing_items.append({
                    "requirement": req,
                    "satisfied": False,
                    "suggested_type": suggested_type,
                    "label": DOCUMENT_TYPES.get(suggested_type, {}).get("label", req),
                })

        total_reqs = len(opp_reqs)
        matched_count = len(matched_items)
        readiness_pct = round((matched_count / max(1, total_reqs)) * 100.0, 1)

        return {
            "opportunity_id": opportunity_id,
            "organization_id": org_id,
            "readiness_pct": readiness_pct,
            "all_satisfied": len(missing_items) == 0,
            "total_requirements": total_reqs,
            "satisfied_count": matched_count,
            "matched_documents": matched_items,
            "missing_documents": missing_items,
            "total_available_documents": len(available_inspections),
        }

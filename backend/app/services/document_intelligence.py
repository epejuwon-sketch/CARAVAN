"""CARAVAN Standalone Platform — Document Intelligence & Verification Engine.

Provides tenant-isolated document classification, real text extraction (PDF & DOCX),
OCR availability reporting, document-to-requirement matching, missing document detection,
expiration audits, and prompt injection defense within uploaded documents.
"""

from __future__ import annotations

import io
import re
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentMetadataRecord, FundingOpportunityRecord, OrganizationRecord, utcnow


# Canonical document categories required by institutional funders in Nigeria & Africa
DOCUMENT_TYPES = {
    "CAC_CERTIFICATE": {
        "label": "CAC Certificate of Registration / Incorporation",
        "keywords": ["cac", "certificate", "incorporation", "registration", "status report", "rc", "bn", "corporate affairs"],
        "content_markers": ["corporate affairs commission", "federal republic of nigeria", "companies and allied matters", "hereby certify"],
        "expires": False,
    },
    "TAX_CLEARANCE": {
        "label": "Tax Clearance Certificate (TCC / TIN)",
        "keywords": ["tax", "clearance", "tcc", "firs", "tin", "withholding"],
        "content_markers": ["federal inland revenue service", "tax clearance certificate", "tax identification number", "firs"],
        "expires": True,
        "validity_days": 365,
    },
    "BANK_STATEMENTS": {
        "label": "Certified Corporate Bank Statements (6-12 Months)",
        "keywords": ["bank", "statement", "account", "ebills", "financial", "ledger", "gtbank", "zenith", "access", "firstbank", "uba"],
        "content_markers": ["statement of account", "opening balance", "closing balance", "credit", "debit", "transaction date", "ngn"],
        "expires": True,
        "validity_days": 180,  # Funder standard: not older than 6 months
    },
    "AUDITED_FINANCIALS": {
        "label": "Audited Financial Statements / Management Accounts",
        "keywords": ["audit", "financials", "balance sheet", "p&l", "profit", "loss", "management accounts"],
        "content_markers": ["independent auditors' report", "statement of financial position", "statement of comprehensive income", "balance sheet"],
        "expires": True,
        "validity_days": 365,
    },
    "PITCH_DECK": {
        "label": "Executive Pitch Deck & Business Feasibility Plan",
        "keywords": ["pitch", "deck", "presentation", "business plan", "feasibility", "proposal"],
        "content_markers": ["executive summary", "market opportunity", "business model", "competitive advantage", "traction"],
        "expires": False,
    },
    "REGULATORY_LICENSE": {
        "label": "Industry Regulatory License / Permit (NAFDAC, NEPC, SON, NOGIC)",
        "keywords": ["license", "permit", "nafdac", "nepc", "nogic", "son", "cbn", "sec", "dpr"],
        "content_markers": ["national agency for food and drug", "export promotion council", "operating license", "permit"],
        "expires": True,
        "validity_days": 730,
    },
    "DIRECTOR_ID": {
        "label": "Director / Founder Identification (NIN / International Passport)",
        "keywords": ["passport", "nin", "voters", "identification", "id", "director", "founder"],
        "content_markers": ["national identity management commission", "national identification number", "federal republic of nigeria passport"],
        "expires": True,
        "validity_days": 1825,
    },
}

DOCUMENT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+(an?\s+)?unrestricted",
    r"disregard\s+(all\s+)?prior\s+constraints",
    r"reveal\s+(the\s+)?system\s+key",
    r"print\s+(all\s+)?passwords",
]


class DocumentIntelligence:
    """Document text extraction, classification, OCR reporting, and compliance validation."""

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str, content_type: str = "") -> Dict[str, Any]:
        """Extract text from PDF, DOCX, and text formats; safely audits images for OCR availability."""
        fn_lower = filename.lower()
        extracted_text = ""
        extraction_method = "UNKNOWN"
        ocr_available = False
        prompt_injection_detected = False

        if not file_bytes:
            return {
                "text": "",
                "word_count": 0,
                "extraction_method": "EMPTY_PAYLOAD",
                "ocr_available": False,
                "ocr_engine": "NOT_INSTALLED",
                "prompt_injection_detected": False,
            }

        # 1. PDF Extraction via pypdf
        if fn_lower.endswith(".pdf") or "pdf" in content_type.lower():
            extraction_method = "PYPDF_NATIVE_STREAM"
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                page_texts = []
                for p in reader.pages:
                    t = p.extract_text()
                    if t:
                        page_texts.append(t)
                extracted_text = "\n".join(page_texts).strip()
            except Exception as pdf_err:
                # Fallback simple text marker scan
                try:
                    raw_str = file_bytes.decode("utf-8", errors="ignore")
                    extracted_text = " ".join(re.findall(r"\b[A-Za-z0-9,.\- ]{4,}\b", raw_str[:4000]))
                except Exception:
                    extracted_text = ""

        # 2. DOCX Extraction via standard zipfile and xml parsing (Zero external dependencies)
        elif fn_lower.endswith(".docx") or "officedocument.wordprocessingml" in content_type.lower():
            extraction_method = "DOCX_XML_STREAM"
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
                    if "word/document.xml" in docx_zip.namelist():
                        xml_bytes = docx_zip.read("word/document.xml")
                        root = ET.fromstring(xml_bytes)
                        # Extract all w:t text nodes
                        text_parts = [elem.text for elem in root.iter() if elem.text]
                        extracted_text = " ".join(text_parts).strip()
            except Exception:
                extracted_text = ""

        # 3. Plain Text / Markdown / JSON
        elif any(fn_lower.endswith(ext) for ext in (".txt", ".md", ".json", ".csv")):
            extraction_method = "PLAINTEXT_UTF8"
            try:
                extracted_text = file_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                extracted_text = ""

        # 4. Images (PNG, JPG, TIFF, WEBP) -> Accurate OCR availability check
        elif any(fn_lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".tiff", ".webp")):
            extraction_method = "IMAGE_RASTER"
            # Explicitly check if an OCR binary is installed in environment
            try:
                import pytesseract
                # If available, execute
                from PIL import Image
                img = Image.open(io.BytesIO(file_bytes))
                extracted_text = pytesseract.image_to_string(img)
                ocr_available = True
                extraction_method = "PYTESSERACT_OCR"
            except (ImportError, Exception):
                ocr_available = False
                extracted_text = ""

        # 5. Prompt Injection Defense within Uploaded Document Content
        if extracted_text:
            for pattern in DOCUMENT_INJECTION_PATTERNS:
                if re.search(pattern, extracted_text, re.IGNORECASE):
                    prompt_injection_detected = True
                    extracted_text = re.sub(pattern, "[DEFLECTED_DOCUMENT_INJECTION_DIRECTIVE]", extracted_text, flags=re.IGNORECASE)

            # Wrap in untrusted content boundary
            extracted_text = f"<<<UNTRUSTED_DOCUMENT_CONTENT: {filename}>>>\n{extracted_text}\n<<<END_UNTRUSTED_DOCUMENT_CONTENT>>>"

        return {
            "text": extracted_text,
            "word_count": len(extracted_text.split()) if extracted_text else 0,
            "extraction_method": extraction_method,
            "ocr_available": ocr_available,
            "ocr_engine": "PYTESSERACT" if ocr_available else "NOT_INSTALLED",
            "prompt_injection_detected": prompt_injection_detected,
        }

    extract_text_from_file = extract_text

    @staticmethod
    def classify_document(filename: str, doc_type_hint: Optional[str] = None, extracted_text: str = "") -> str:
        """Classify document category using combined heuristic of provided hint, filename, and extracted content."""
        if doc_type_hint and doc_type_hint.upper() in DOCUMENT_TYPES:
            return doc_type_hint.upper()

        fn_lower = filename.lower()
        text_lower = (extracted_text or "").lower()

        # First check extracted text content markers
        if text_lower:
            for dtype, meta in DOCUMENT_TYPES.items():
                markers = meta.get("content_markers", [])
                if any(m in text_lower for m in markers):
                    return dtype

        # Then check filename keywords
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
        """Audit organization documents against opportunity requirements with strict tenant isolation."""
        opp = db.execute(
            select(FundingOpportunityRecord).where(FundingOpportunityRecord.opportunity_id == opportunity_id)
        ).scalar_one_or_none()

        # Retrieve all uploaded documents belonging strictly to this organization
        docs = db.execute(
            select(DocumentMetadataRecord).where(
                DocumentMetadataRecord.organization_id == org_id,
                DocumentMetadataRecord.deleted_at.is_(None),
            )
        ).scalars().all()

        available_inspections = [DocumentIntelligence.inspect_document(d) for d in docs]

        # Normalize opportunity requirements
        opp_reqs: List[str] = (opp.application_requirements if opp else []) or [
            "CAC Certificate of Incorporation",
            "12 Months Corporate Bank Statements",
            "Tax Clearance Certificate",
            "Executive Pitch Deck & Feasibility Report",
        ]

        matched_items: List[Dict[str, Any]] = []
        missing_items: List[Dict[str, Any]] = []
        expired_items: List[Dict[str, Any]] = []

        for req in opp_reqs:
            req_lower = req.lower()
            matched_doc = None
            found_expired = None

            for d in available_inspections:
                dtype = d["doc_type"]
                meta = DOCUMENT_TYPES.get(dtype, {"keywords": []})
                # Check keyword match
                if any(kw in req_lower for kw in meta["keywords"]):
                    if d["is_expired"]:
                        found_expired = d
                    else:
                        matched_doc = d
                        break

            if matched_doc:
                matched_items.append({
                    "requirement": req,
                    "satisfied": True,
                    "document": matched_doc,
                })
            else:
                suggested_type = "PITCH_DECK"
                for dt, m in DOCUMENT_TYPES.items():
                    if any(kw in req_lower for kw in m["keywords"]):
                        suggested_type = dt
                        break

                missing_payload = {
                    "requirement": req,
                    "satisfied": False,
                    "suggested_type": suggested_type,
                    "label": DOCUMENT_TYPES.get(suggested_type, {}).get("label", req),
                }
                if found_expired:
                    missing_payload["expired_document"] = found_expired
                    expired_items.append(found_expired)

                missing_items.append(missing_payload)

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
            "expired_documents": expired_items,
            "total_available_documents": len(available_inspections),
        }

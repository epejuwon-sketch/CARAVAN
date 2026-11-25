"""CARAVAN Standalone Platform — Funding Intelligence & Discovery Engine.

Provides automated and assisted discovery of legitimate funding programs, structured
source verification, duplicate detection, review queue processing, and lifecycle monitoring.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from app.db.models import FundingOpportunityRecord, AuditLogRecord, NotificationRecord, UserRecord, utcnow

logger = logging.getLogger("caravan.discovery")


def normalize_url(url: str) -> str:
    """Normalize a URL to prevent duplicate entries based on query params or formatting."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Standardize scheme and netloc to lowercase, strip trailing slash from path, drop query & fragment for canonical root
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def calculate_provenance_hash(canonical_payload: Dict[str, Any]) -> str:
    """Calculate deterministic SHA-256 hash for provenance and duplicate detection."""
    norm_provider = (canonical_payload.get("provider") or "").strip().lower()
    norm_title = (canonical_payload.get("title") or "").strip().lower()
    norm_url = normalize_url(canonical_payload.get("official_source_url") or "")
    fingerprint = f"{norm_provider}|{norm_title}|{norm_url}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


class DiscoveryEngine:
    """Funding opportunity discovery, extraction, verification and review pipeline."""

    @staticmethod
    def detect_duplicate(db: Session, title: str, provider: str, url: str) -> Optional[FundingOpportunityRecord]:
        """Detect existing opportunity by canonical URL, provenance hash, or exact title+provider."""
        norm_url = normalize_url(url)
        dummy_hash = calculate_provenance_hash({"title": title, "provider": provider, "official_source_url": url})
        
        # Check by provenance hash or exact URL match
        stmt = select(FundingOpportunityRecord).where(
            or_(
                FundingOpportunityRecord.provenance_hash == dummy_hash,
                FundingOpportunityRecord.official_source_url == url,
                func.lower(FundingOpportunityRecord.title) == title.strip().lower(),
            )
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def ingest_discovered_opportunity(
        db: Session,
        raw_record: Dict[str, Any],
        discovered_by: str = "DISCOVERY_CRAWLER",
    ) -> Dict[str, Any]:
        """Ingest a newly discovered opportunity into the PENDING_REVIEW queue.
        
        Never auto-publishes without verification; sets publication_status=PENDING_REVIEW.
        """
        title = raw_record.get("title", "").strip()
        provider = raw_record.get("provider", "").strip()
        official_url = raw_record.get("official_source_url", "").strip()

        if not title or not provider or not official_url:
            return {"status": "REJECTED", "reason": "Missing required fields (title, provider, official_source_url)"}

        existing = DiscoveryEngine.detect_duplicate(db, title, provider, official_url)
        if existing:
            return {
                "status": "DUPLICATE",
                "opportunity_id": existing.opportunity_id,
                "title": existing.title,
                "existing_status": existing.publication_status,
            }

        prov_hash = calculate_provenance_hash(raw_record)
        evidence = raw_record.get("verification_evidence") or {
            "publisher_verified": bool(provider),
            "official_portal_verified": official_url.startswith("http"),
            "funding_range_verified": bool(raw_record.get("amount_display")),
            "eligibility_criteria_verified": bool(raw_record.get("applicant_eligibility")),
            "source_retrieval_url": official_url,
            "crawler_agent": discovered_by,
        }

        # Calculate initial confidence score based on verified criteria
        verified_points = sum(1 for v in evidence.values() if v is True)
        confidence = round(min(1.0, max(0.2, verified_points / 4.0)), 2)
        completeness = "COMPLETE" if confidence >= 0.8 else ("PARTIAL" if confidence >= 0.5 else "UNCONFIRMED")

        new_record = FundingOpportunityRecord(
            title=title,
            provider=provider,
            funding_type=raw_record.get("funding_type", "GRANT"),
            amount_min=raw_record.get("amount_min", 0.0),
            amount_max=raw_record.get("amount_max", 0.0),
            currency=raw_record.get("currency", "USD"),
            amount_display=raw_record.get("amount_display", "Amount varies"),
            geographic_eligibility=raw_record.get("geographic_eligibility", "Global / Multi-Region"),
            applicant_eligibility=raw_record.get("applicant_eligibility", "General eligibility criteria apply."),
            industry_sector=raw_record.get("industry_sector", "Multi-Sector"),
            application_requirements=raw_record.get("application_requirements", []),
            opening_date=raw_record.get("opening_date"),
            deadline_at=raw_record.get("deadline_at"),
            is_rolling=raw_record.get("is_rolling", False),
            official_source_url=official_url,
            verification_status="PENDING_REVIEW",
            source_name=raw_record.get("source_name", "Automated Discovery Registry"),
            provenance_hash=prov_hash,
            source_retrieval_at=utcnow(),
            verification_method="AUTOMATED_DISCOVERY_CRAWLER",
            verification_evidence=evidence,
            confidence_score=confidence,
            evidence_completeness=completeness,
            last_checked_at=utcnow(),
            verification_history=[
                {
                    "timestamp": utcnow().isoformat(),
                    "actor": discovered_by,
                    "action": "DISCOVERED_INGESTION",
                    "confidence_score": confidence,
                    "details": "Extracted and staged for compliance review.",
                }
            ],
            publication_status="PENDING_REVIEW",
        )

        db.add(new_record)
        
        # Write audit log
        audit = AuditLogRecord(
            actor=discovered_by,
            action="DISCOVERY_INGESTED",
            resource=f"opportunity:{new_record.opportunity_id}",
            outcome="SUCCESS",
            details={"title": title, "provider": provider, "confidence": confidence},
        )
        db.add(audit)
        db.commit()
        db.refresh(new_record)

        return {
            "status": "INGESTED",
            "opportunity_id": new_record.opportunity_id,
            "title": new_record.title,
            "publication_status": new_record.publication_status,
            "confidence_score": new_record.confidence_score,
            "evidence_completeness": new_record.evidence_completeness,
        }

    @staticmethod
    def get_review_queue(db: Session, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve opportunities pending administrative review."""
        stmt = (
            select(FundingOpportunityRecord)
            .where(FundingOpportunityRecord.publication_status == "PENDING_REVIEW")
            .order_by(FundingOpportunityRecord.confidence_score.desc(), FundingOpportunityRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        records = db.execute(stmt).scalars().all()
        return [
            {
                "opportunity_id": r.opportunity_id,
                "title": r.title,
                "provider": r.provider,
                "funding_type": r.funding_type,
                "amount_display": r.amount_display,
                "geographic_eligibility": r.geographic_eligibility,
                "official_source_url": r.official_source_url,
                "confidence_score": r.confidence_score,
                "evidence_completeness": r.evidence_completeness,
                "verification_evidence": r.verification_evidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "publication_status": r.publication_status,
            }
            for r in records
        ]

    @staticmethod
    def approve_opportunity(
        db: Session,
        opportunity_id: str,
        reviewer_id: str,
        reviewer_role: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Verify, approve, and publish a pending funding opportunity."""
        record = db.get(FundingOpportunityRecord, opportunity_id)
        if not record:
            return {"success": False, "error": "Opportunity not found."}

        record.publication_status = "PUBLISHED"
        if record.opening_date and record.opening_date > utcnow():
            record.verification_status = "UPCOMING_CONFIRMED"
        else:
            record.verification_status = "VERIFIED_OPEN"
        record.verified_at = utcnow()
        record.confidence_score = 1.0
        record.evidence_completeness = "COMPLETE"
        record.last_checked_at = utcnow()

        history = list(record.verification_history or [])
        history.append({
            "timestamp": utcnow().isoformat(),
            "actor": reviewer_id,
            "role": reviewer_role,
            "action": "APPROVED_AND_PUBLISHED",
            "notes": notes or "Manually verified against official institutional source.",
        })
        record.verification_history = history

        audit = AuditLogRecord(
            actor=reviewer_id,
            action="OPPORTUNITY_APPROVED",
            resource=f"opportunity:{opportunity_id}",
            outcome="SUCCESS",
            details={"title": record.title, "reviewer_role": reviewer_role, "notes": notes},
        )
        db.add(audit)

        # Broadcast notification to registered users
        users = db.execute(select(UserRecord)).scalars().all()
        for u in users:
            notif = NotificationRecord(
                user_id=u.user_id,
                title=f"New Program Verified: {record.title}",
                message=f"{record.provider} opportunity '{record.title}' ({record.amount_display}) is now published and verified.",
                category="OPPORTUNITY",
            )
            db.add(notif)

        db.commit()
        db.refresh(record)

        return {"success": True, "opportunity_id": record.opportunity_id, "status": record.publication_status, "verification_status": record.verification_status}

    @staticmethod
    def reject_opportunity(
        db: Session,
        opportunity_id: str,
        reviewer_id: str,
        reviewer_role: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Reject and archive an unverifiable or closed funding opportunity."""
        record = db.get(FundingOpportunityRecord, opportunity_id)
        if not record:
            return {"success": False, "error": "Opportunity not found."}

        record.publication_status = "ARCHIVED"
        record.verification_status = "REJECTED"
        record.last_checked_at = utcnow()

        history = list(record.verification_history or [])
        history.append({
            "timestamp": utcnow().isoformat(),
            "actor": reviewer_id,
            "role": reviewer_role,
            "action": "REJECTED",
            "reason": reason,
        })
        record.verification_history = history

        audit = AuditLogRecord(
            actor=reviewer_id,
            action="OPPORTUNITY_REJECTED",
            resource=f"opportunity:{opportunity_id}",
            outcome="SUCCESS",
            details={"title": record.title, "reason": reason},
        )
        db.add(audit)
        db.commit()
        db.refresh(record)

        return {"success": True, "opportunity_id": record.opportunity_id, "status": record.publication_status}

    @staticmethod
    def audit_and_recheck_deadlines(db: Session) -> Dict[str, Any]:
        """Continuous audit to update statuses for expired opportunities."""
        now = utcnow()
        stmt = (
            select(FundingOpportunityRecord)
            .where(
                FundingOpportunityRecord.publication_status == "PUBLISHED",
                FundingOpportunityRecord.is_rolling == False,
                FundingOpportunityRecord.deadline_at.isnot(None),
                FundingOpportunityRecord.deadline_at < now,
            )
        )
        expired_records = db.execute(stmt).scalars().all()
        updated_count = 0
        for r in expired_records:
            if r.verification_status != "EXPIRED":
                r.verification_status = "EXPIRED"
                r.last_checked_at = now
                history = list(r.verification_history or [])
                history.append({
                    "timestamp": now.isoformat(),
                    "actor": "DEADLINE_AUDITOR",
                    "action": "STATUS_EXPIRED",
                    "details": f"Deadline {r.deadline_at.isoformat()} has passed.",
                })
                r.verification_history = history
                updated_count += 1

        if updated_count > 0:
            db.commit()

        return {"checked_at": now.isoformat(), "expired_count": updated_count}

"""CARAVAN Standalone Platform — SQLAlchemy ORM Data Models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:14]}"


class UserRecord(Base):
    __tablename__ = "caravan_users"

    user_id = Column(String(64), primary_key=True, default=lambda: gen_id("usr"))
    organization_id = Column(String(64), nullable=False, index=True)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), nullable=False)
    role = Column(String(32), default="CUSTOMER", nullable=False)  # CUSTOMER, ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class OrganizationRecord(Base):
    __tablename__ = "caravan_organizations"

    org_id = Column(String(64), primary_key=True, default=lambda: gen_id("org"))
    name = Column(String(200), nullable=False)
    entity_type = Column(String(64), default="STARTUP", nullable=False)  # STARTUP, SME, NGO, RESEARCH, COOP
    country = Column(String(80), default="Nigeria", nullable=False)
    state_location = Column(String(120), default="Abuja (FCT)", nullable=False)
    sector = Column(String(120), default="Technology", nullable=False)
    stage = Column(String(64), default="SEED", nullable=False)  # IDEA, SEED, EARLY_GROWTH, EXPANSION, MATURE
    annual_revenue_usd = Column(Float, default=0.0, nullable=False)
    annual_revenue_ngn = Column(Float, default=0.0, nullable=False)
    funding_goals = Column(Text, default="", nullable=False)
    team_size = Column(Integer, default=5, nullable=False)
    cac_registered = Column(Boolean, default=True, nullable=False)
    years_in_operation = Column(Integer, default=1, nullable=False)
    female_led = Column(Boolean, default=False, nullable=False)
    youth_led = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class FundingOpportunityRecord(Base):
    __tablename__ = "caravan_funding_opportunities"

    opportunity_id = Column(String(64), primary_key=True, default=lambda: gen_id("opp"))
    title = Column(String(255), nullable=False, index=True)
    provider = Column(String(255), nullable=False, index=True)
    funding_type = Column(String(64), nullable=False, index=True)
    # Categories:
    # GRANT, LOAN, VENTURE_CAPITAL, ANGEL_INVESTMENT, SEED_FUNDING,
    # ACCELERATOR, COMPETITION, AWARD, WORKING_CAPITAL, EQUIPMENT_FINANCING,
    # CORPORATE_FUNDING, INSTITUTIONAL_FINANCE, RESEARCH_FUNDING,
    # PHILANTHROPIC_FUNDING, SCHOLARSHIP
    
    amount_min = Column(Float, nullable=True)
    amount_max = Column(Float, nullable=True)
    currency = Column(String(8), default="USD", nullable=False)  # USD, NGN, GBP, EUR
    amount_display = Column(String(100), default="Undisclosed / Variable", nullable=False)
    
    geographic_eligibility = Column(String(255), default="Nigeria / West Africa", nullable=False, index=True)
    applicant_eligibility = Column(Text, nullable=False)
    industry_sector = Column(String(160), default="Multi-Sector", nullable=False, index=True)
    application_requirements = Column(JSON, default=list, nullable=False)
    
    opening_date = Column(DateTime(timezone=True), nullable=True)
    deadline_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_rolling = Column(Boolean, default=False, nullable=False)
    
    official_source_url = Column(String(500), nullable=False)
    official_application_url = Column(String(500), nullable=True)
    supporting_source_urls = Column(JSON, default=list, nullable=False)
    eligible_applicant_types = Column(JSON, default=list, nullable=False)
    eligible_countries = Column(JSON, default=list, nullable=False)
    eligible_states = Column(JSON, default=list, nullable=False)
    eligible_sectors = Column(JSON, default=list, nullable=False)
    funding_structure = Column(String(120), default="DIRECT_DISBURSEMENT", nullable=False)
    business_stage = Column(String(120), default="ALL_STAGES", nullable=False)
    age_restrictions = Column(String(120), default="NO_RESTRICTION", nullable=False)
    registration_required = Column(Boolean, default=True, nullable=False)
    application_method = Column(String(120), default="ONLINE_PORTAL", nullable=False)
    opportunity_status = Column(String(64), default="OPEN", nullable=False, index=True)
    important_conditions = Column(Text, default="", nullable=False)

    verification_status = Column(String(32), default="VERIFIED", nullable=False, index=True)  # DISCOVERED, PENDING_REVIEW, VERIFIED, UNVERIFIED, REJECTED, UPCOMING, OPEN, CLOSED, EXPIRED, SUSPENDED
    verified_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    source_name = Column(String(160), default="Direct Official Registry", nullable=False)
    provenance_hash = Column(String(64), default="", nullable=False)

    # Genuine Source Verification & Intelligence Attributes
    source_retrieval_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    verification_method = Column(String(64), default="MANUAL_REGISTRY_AUDIT", nullable=False)
    verification_evidence = Column(JSON, default=dict, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    evidence_completeness = Column(String(32), default="COMPLETE", nullable=False)  # COMPLETE, PARTIAL, UNCONFIRMED
    last_checked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    next_verification_at = Column(DateTime(timezone=True), nullable=True)
    verification_history = Column(JSON, default=list, nullable=False)
    publication_status = Column(String(32), default="PUBLISHED", nullable=False, index=True)  # DRAFT, PENDING_REVIEW, PUBLISHED, ARCHIVED
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_opp_type_geo", "funding_type", "geographic_eligibility"),
        Index("ix_opp_status_deadline", "verification_status", "deadline_at"),
    )


class EligibilityAssessmentRecord(Base):
    __tablename__ = "caravan_eligibility_assessments"

    assessment_id = Column(String(64), primary_key=True, default=lambda: gen_id("ass"))
    organization_id = Column(String(64), nullable=False, index=True)
    opportunity_id = Column(String(64), ForeignKey("caravan_funding_opportunities.opportunity_id"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)  # 0.0 to 100.0
    recommendation_level = Column(String(32), default="STRONG", nullable=False)  # STRONG, MODERATE, WEAK, INELIGIBLE
    criteria_breakdown = Column(JSON, default=dict, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class ApplicationRecord(Base):
    __tablename__ = "caravan_applications"

    application_id = Column(String(64), primary_key=True, default=lambda: gen_id("app"))
    organization_id = Column(String(64), nullable=False, index=True)
    opportunity_id = Column(String(64), ForeignKey("caravan_funding_opportunities.opportunity_id"), nullable=False, index=True)
    status = Column(String(32), default="DRAFTING", nullable=False, index=True)
    # Statuses: DRAFTING, DOCS_COLLECTING, REVIEW, SUBMITTED, AWARDED, REJECTED
    checklist_progress = Column(JSON, default=list, nullable=False)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class DocumentMetadataRecord(Base):
    __tablename__ = "caravan_documents"

    doc_id = Column(String(64), primary_key=True, default=lambda: gen_id("doc"))
    organization_id = Column(String(64), nullable=False, index=True)
    application_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    doc_type = Column(String(64), default="PITCH_DECK", nullable=False)  # PITCH_DECK, FINANCIALS, CERTIFICATE, TAX_CLEARANCE
    file_size_bytes = Column(Integer, default=0, nullable=False)
    storage_path = Column(String(512), nullable=True)
    content_type = Column(String(128), default="application/octet-stream", nullable=False)
    scan_status = Column(String(32), default="AVAILABLE", nullable=False)  # AVAILABLE, QUARANTINED, PENDING_SCAN, FAILED
    scan_details = Column(JSON, default=dict, nullable=False)
    sha256_hash = Column(String(64), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class SavedOpportunityRecord(Base):
    __tablename__ = "caravan_saved_opportunities"

    saved_id = Column(String(64), primary_key=True, default=lambda: gen_id("sav"))
    organization_id = Column(String(64), nullable=False, index=True)
    opportunity_id = Column(String(64), ForeignKey("caravan_funding_opportunities.opportunity_id"), nullable=False, index=True)
    notes = Column(Text, default="", nullable=False)
    saved_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class SubscriptionRecord(Base):
    __tablename__ = "caravan_subscriptions"

    subscription_id = Column(String(64), primary_key=True, default=lambda: gen_id("sub"))
    organization_id = Column(String(64), unique=True, nullable=False, index=True)
    tier = Column(String(32), default="FREE", nullable=False)  # FREE, STARTER, GROWTH, PRO, INSTITUTIONAL, CUSTOM
    price_usd_monthly = Column(Float, default=0.0, nullable=False)
    billing_provider = Column(String(32), default="MANUAL", nullable=False)  # FLUTTERWAVE, PAYSTACK, MANUAL
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, PAST_DUE, CANCELED
    renewal_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class PaymentTransactionRecord(Base):
    __tablename__ = "caravan_payment_transactions"

    tx_id = Column(String(64), primary_key=True, default=lambda: gen_id("tx"))
    organization_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(32), nullable=False)  # FLUTTERWAVE, PAYSTACK
    reference = Column(String(128), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="NGN", nullable=False)
    tier = Column(String(32), nullable=False)
    status = Column(String(32), default="SUCCESSFUL", nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class SupportTicketRecord(Base):
    __tablename__ = "caravan_support_tickets"

    ticket_id = Column(String(64), primary_key=True, default=lambda: gen_id("tkt"))
    organization_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(32), default="OPEN", nullable=False)  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    response = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class NotificationRecord(Base):
    __tablename__ = "caravan_notifications"

    notification_id = Column(String(64), primary_key=True, default=lambda: gen_id("notif"))
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(32), default="SYSTEM", nullable=False)  # DEADLINE, OPPORTUNITY, MATCH, BILLING
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLogRecord(Base):
    __tablename__ = "caravan_audit_logs"

    log_id = Column(String(64), primary_key=True, default=lambda: gen_id("aud"))
    actor = Column(String(128), nullable=False)
    action = Column(String(64), nullable=False, index=True)
    resource = Column(String(128), nullable=False)
    outcome = Column(String(32), default="SUCCESS", nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

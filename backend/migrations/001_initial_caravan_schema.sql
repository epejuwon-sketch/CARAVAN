-- ==============================================================================
-- CARAVAN Standalone Platform — Initial PostgreSQL Schema Migration
-- Migration: 001_initial_caravan_schema.sql
-- ==============================================================================

CREATE TABLE IF NOT EXISTS caravan_users (
    user_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    email VARCHAR(160) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'CUSTOMER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_users_org ON caravan_users (organization_id);
CREATE INDEX IF NOT EXISTS ix_caravan_users_email ON caravan_users (email);

CREATE TABLE IF NOT EXISTS caravan_organizations (
    org_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(64) NOT NULL DEFAULT 'STARTUP',
    country VARCHAR(80) NOT NULL DEFAULT 'Nigeria',
    state_location VARCHAR(120) NOT NULL DEFAULT 'Abuja (FCT)',
    sector VARCHAR(120) NOT NULL DEFAULT 'Technology',
    stage VARCHAR(64) NOT NULL DEFAULT 'SEED',
    annual_revenue_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    funding_goals TEXT NOT NULL DEFAULT '',
    team_size INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS caravan_funding_opportunities (
    opportunity_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    funding_type VARCHAR(64) NOT NULL,
    amount_min DOUBLE PRECISION,
    amount_max DOUBLE PRECISION,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    amount_display VARCHAR(100) NOT NULL DEFAULT 'Undisclosed / Variable',
    geographic_eligibility VARCHAR(255) NOT NULL DEFAULT 'Nigeria / West Africa',
    applicant_eligibility TEXT NOT NULL,
    industry_sector VARCHAR(160) NOT NULL DEFAULT 'Multi-Sector',
    application_requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    opening_date TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ,
    is_rolling BOOLEAN NOT NULL DEFAULT FALSE,
    official_source_url VARCHAR(500) NOT NULL,
    verification_status VARCHAR(32) NOT NULL DEFAULT 'VERIFIED',
    verified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_name VARCHAR(160) NOT NULL DEFAULT 'Direct Official Registry',
    provenance_hash VARCHAR(64) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_opp_title ON caravan_funding_opportunities (title);
CREATE INDEX IF NOT EXISTS ix_caravan_opp_provider ON caravan_funding_opportunities (provider);
CREATE INDEX IF NOT EXISTS ix_caravan_opp_type ON caravan_funding_opportunities (funding_type);
CREATE INDEX IF NOT EXISTS ix_caravan_opp_geo ON caravan_funding_opportunities (geographic_eligibility);
CREATE INDEX IF NOT EXISTS ix_caravan_opp_status ON caravan_funding_opportunities (verification_status);
CREATE INDEX IF NOT EXISTS ix_caravan_opp_deadline ON caravan_funding_opportunities (deadline_at);

CREATE TABLE IF NOT EXISTS caravan_eligibility_assessments (
    assessment_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    opportunity_id VARCHAR(64) NOT NULL REFERENCES caravan_funding_opportunities(opportunity_id) ON DELETE CASCADE,
    match_score DOUBLE PRECISION NOT NULL,
    recommendation_level VARCHAR(32) NOT NULL DEFAULT 'STRONG',
    criteria_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_ass_org ON caravan_eligibility_assessments (organization_id);
CREATE INDEX IF NOT EXISTS ix_caravan_ass_opp ON caravan_eligibility_assessments (opportunity_id);

CREATE TABLE IF NOT EXISTS caravan_applications (
    application_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    opportunity_id VARCHAR(64) NOT NULL REFERENCES caravan_funding_opportunities(opportunity_id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFTING',
    checklist_progress JSONB NOT NULL DEFAULT '[]'::jsonb,
    deadline_at TIMESTAMPTZ,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_app_org ON caravan_applications (organization_id);
CREATE INDEX IF NOT EXISTS ix_caravan_app_opp ON caravan_applications (opportunity_id);
CREATE INDEX IF NOT EXISTS ix_caravan_app_status ON caravan_applications (status);

CREATE TABLE IF NOT EXISTS caravan_documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    application_id VARCHAR(64),
    name VARCHAR(255) NOT NULL,
    doc_type VARCHAR(64) NOT NULL DEFAULT 'PITCH_DECK',
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_doc_org ON caravan_documents (organization_id);
CREATE INDEX IF NOT EXISTS ix_caravan_doc_app ON caravan_documents (application_id);

CREATE TABLE IF NOT EXISTS caravan_saved_opportunities (
    saved_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    opportunity_id VARCHAR(64) NOT NULL REFERENCES caravan_funding_opportunities(opportunity_id) ON DELETE CASCADE,
    notes TEXT NOT NULL DEFAULT '',
    saved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_saved_org ON caravan_saved_opportunities (organization_id);
CREATE INDEX IF NOT EXISTS ix_caravan_saved_opp ON caravan_saved_opportunities (opportunity_id);

CREATE TABLE IF NOT EXISTS caravan_subscriptions (
    subscription_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) UNIQUE NOT NULL,
    tier VARCHAR(32) NOT NULL DEFAULT 'FREE',
    price_usd_monthly DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    billing_provider VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    renewal_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS caravan_payment_transactions (
    tx_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    reference VARCHAR(128) UNIQUE NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'NGN',
    tier VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESSFUL',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_tx_org ON caravan_payment_transactions (organization_id);
CREATE INDEX IF NOT EXISTS ix_caravan_tx_ref ON caravan_payment_transactions (reference);

CREATE TABLE IF NOT EXISTS caravan_support_tickets (
    ticket_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    response TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_tkt_org ON caravan_support_tickets (organization_id);

CREATE TABLE IF NOT EXISTS caravan_notifications (
    notification_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'SYSTEM',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_notif_user ON caravan_notifications (user_id);

CREATE TABLE IF NOT EXISTS caravan_audit_logs (
    log_id VARCHAR(64) PRIMARY KEY,
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    resource VARCHAR(128) NOT NULL,
    outcome VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_caravan_aud_action ON caravan_audit_logs (action);

-- Enable Row Level Security (RLS) for Multi-Tenant Isolation
ALTER TABLE caravan_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_eligibility_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_saved_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_notifications ENABLE ROW LEVEL SECURITY;

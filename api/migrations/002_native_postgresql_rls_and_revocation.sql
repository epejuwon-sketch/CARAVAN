-- ==============================================================================
-- CARAVAN Standalone Platform — Native PostgreSQL RLS & Token Revocation
-- Migration: 002_native_postgresql_rls_and_revocation.sql
-- ==============================================================================

-- 0. Schema Migration Tracking Table
CREATE TABLE IF NOT EXISTS caravan_schema_migrations (
    migration_id VARCHAR(120) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO caravan_schema_migrations (migration_id, applied_at)
VALUES ('002_native_postgresql_rls_and_revocation', CURRENT_TIMESTAMP)
ON CONFLICT (migration_id) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

-- 1. Distributed Rate Limiting Table
CREATE TABLE IF NOT EXISTS caravan_rate_limits (
    bucket_key VARCHAR(160) PRIMARY KEY,
    request_count INTEGER NOT NULL DEFAULT 1,
    window_start_epoch DOUBLE PRECISION NOT NULL,
    last_request_epoch DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_caravan_rate_limits_window ON caravan_rate_limits (window_start_epoch);

-- 2. Multi-Instance Token Revocation Store
CREATE TABLE IF NOT EXISTS caravan_revoked_tokens (
    token_jti VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_caravan_revoked_tokens_user ON caravan_revoked_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_caravan_revoked_tokens_exp ON caravan_revoked_tokens (expires_at);

-- 3. User Revocation Timestamp & Token Version Tracking
ALTER TABLE caravan_users ADD COLUMN IF NOT EXISTS revoked_before_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE caravan_users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 1;

-- 4. Application Restricted Role & Administrator Role Separation
DO $$
BEGIN
    -- caravan_app: unprivileged role for ordinary tenant traffic (strictly NOBYPASSRLS)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'caravan_app') THEN
        CREATE ROLE caravan_app WITH NOSUPERUSER NOINHERIT NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    GRANT USAGE ON SCHEMA public TO caravan_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO caravan_app;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO caravan_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO caravan_app;

    -- caravan_admin: explicitly scoped platform admin role (NOBYPASSRLS, requires membership check)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'caravan_admin') THEN
        CREATE ROLE caravan_admin WITH NOSUPERUSER NOINHERIT NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    END IF;
    GRANT USAGE ON SCHEMA public TO caravan_admin;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO caravan_admin;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO caravan_admin;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO caravan_admin;

    -- Grant roles to connection owner, NEVER grant caravan_admin to caravan_app
    BEGIN
        EXECUTE format('GRANT caravan_app TO %I', CURRENT_USER);
        EXECUTE format('GRANT caravan_admin TO %I', CURRENT_USER);
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;
END $$;

-- 5. Native PostgreSQL Row-Level Security Policies

-- Helper: drop policies if they exist (for idempotent execution)
DO $$
BEGIN
    -- caravan_organizations
    DROP POLICY IF EXISTS tenant_isolation_org ON caravan_organizations;
    CREATE POLICY tenant_isolation_org ON caravan_organizations
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND org_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND org_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_users
    DROP POLICY IF EXISTS tenant_isolation_users ON caravan_users;
    CREATE POLICY tenant_isolation_users ON caravan_users
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_eligibility_assessments
    DROP POLICY IF EXISTS tenant_isolation_eligibility ON caravan_eligibility_assessments;
    CREATE POLICY tenant_isolation_eligibility ON caravan_eligibility_assessments
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_applications
    DROP POLICY IF EXISTS tenant_isolation_apps ON caravan_applications;
    CREATE POLICY tenant_isolation_apps ON caravan_applications
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_documents
    DROP POLICY IF EXISTS tenant_isolation_docs ON caravan_documents;
    CREATE POLICY tenant_isolation_docs ON caravan_documents
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_saved_opportunities
    DROP POLICY IF EXISTS tenant_isolation_saved ON caravan_saved_opportunities;
    CREATE POLICY tenant_isolation_saved ON caravan_saved_opportunities
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_subscriptions
    DROP POLICY IF EXISTS tenant_isolation_subs ON caravan_subscriptions;
    CREATE POLICY tenant_isolation_subs ON caravan_subscriptions
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_payment_transactions
    DROP POLICY IF EXISTS tenant_isolation_tx ON caravan_payment_transactions;
    CREATE POLICY tenant_isolation_tx ON caravan_payment_transactions
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_support_tickets
    DROP POLICY IF EXISTS tenant_isolation_tickets ON caravan_support_tickets;
    CREATE POLICY tenant_isolation_tickets ON caravan_support_tickets
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                AND organization_id = current_setting('app.current_org_id', true)
            )
        );

    -- caravan_notifications
    DROP POLICY IF EXISTS tenant_isolation_notif ON caravan_notifications;
    CREATE POLICY tenant_isolation_notif ON caravan_notifications
        FOR ALL
        USING (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_user_id', true), '') IS NOT NULL
                AND user_id = current_setting('app.current_user_id', true)
            )
        )
        WITH CHECK (
            (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
            OR (
                NULLIF(current_setting('app.current_user_id', true), '') IS NOT NULL
                AND user_id = current_setting('app.current_user_id', true)
            )
        );

    -- caravan_copilot_approvals
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'caravan_copilot_approvals') THEN
        ALTER TABLE caravan_copilot_approvals ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS tenant_isolation_approvals ON caravan_copilot_approvals;
        CREATE POLICY tenant_isolation_approvals ON caravan_copilot_approvals
            FOR ALL
            USING (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            )
            WITH CHECK (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            );
        ALTER TABLE caravan_copilot_approvals FORCE ROW LEVEL SECURITY;
    END IF;

    -- caravan_copilot_submissions
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'caravan_copilot_submissions') THEN
        ALTER TABLE caravan_copilot_submissions ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS tenant_isolation_submissions ON caravan_copilot_submissions;
        CREATE POLICY tenant_isolation_submissions ON caravan_copilot_submissions
            FOR ALL
            USING (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            )
            WITH CHECK (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            );
        ALTER TABLE caravan_copilot_submissions FORCE ROW LEVEL SECURITY;
    END IF;

    -- caravan_copilot_sessions
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'caravan_copilot_sessions') THEN
        ALTER TABLE caravan_copilot_sessions ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS tenant_isolation_sessions ON caravan_copilot_sessions;
        CREATE POLICY tenant_isolation_sessions ON caravan_copilot_sessions
            FOR ALL
            USING (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            )
            WITH CHECK (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            );
        ALTER TABLE caravan_copilot_sessions FORCE ROW LEVEL SECURITY;
    END IF;

    -- caravan_application_drafts
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'caravan_application_drafts') THEN
        ALTER TABLE caravan_application_drafts ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS tenant_isolation_drafts ON caravan_application_drafts;
        CREATE POLICY tenant_isolation_drafts ON caravan_application_drafts
            FOR ALL
            USING (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            )
            WITH CHECK (
                (pg_has_role(CURRENT_USER, 'caravan_admin', 'USAGE') AND current_setting('app.is_admin', true) = 'true')
                OR (
                    NULLIF(current_setting('app.current_org_id', true), '') IS NOT NULL
                    AND organization_id = current_setting('app.current_org_id', true)
                )
            );
        ALTER TABLE caravan_application_drafts FORCE ROW LEVEL SECURITY;
    END IF;

END $$;

-- 5. Enforce ENABLE and FORCE ROW LEVEL SECURITY across all tenant tables
-- ENABLE turns on RLS evaluation; FORCE ensures table owners and db roles are strictly bounded
ALTER TABLE caravan_organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_users FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_eligibility_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_eligibility_assessments FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_applications FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_saved_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_saved_opportunities FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_subscriptions FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_payment_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_payment_transactions FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_support_tickets FORCE ROW LEVEL SECURITY;
ALTER TABLE caravan_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE caravan_notifications FORCE ROW LEVEL SECURITY;

-- ==============================================================================
-- ROLLBACK SPECIFICATION (002_rollback.sql):
-- ==============================================================================
-- To roll back this migration in PostgreSQL:
--
-- ALTER TABLE caravan_organizations NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_users NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_eligibility_assessments NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_applications NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_documents NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_saved_opportunities NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_subscriptions NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_payment_transactions NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_support_tickets NO FORCE ROW LEVEL SECURITY;
-- ALTER TABLE caravan_notifications NO FORCE ROW LEVEL SECURITY;
--
-- DROP POLICY IF EXISTS tenant_isolation_org ON caravan_organizations;
-- DROP POLICY IF EXISTS tenant_isolation_users ON caravan_users;
-- DROP POLICY IF EXISTS tenant_isolation_eligibility ON caravan_eligibility_assessments;
-- DROP POLICY IF EXISTS tenant_isolation_apps ON caravan_applications;
-- DROP POLICY IF EXISTS tenant_isolation_docs ON caravan_documents;
-- DROP POLICY IF EXISTS tenant_isolation_saved ON caravan_saved_opportunities;
-- DROP POLICY IF EXISTS tenant_isolation_subs ON caravan_subscriptions;
-- DROP POLICY IF EXISTS tenant_isolation_tx ON caravan_payment_transactions;
-- DROP POLICY IF EXISTS tenant_isolation_tickets ON caravan_support_tickets;
-- DROP POLICY IF EXISTS tenant_isolation_notif ON caravan_notifications;
--
-- DROP TABLE IF EXISTS caravan_rate_limits;
-- DROP TABLE IF EXISTS caravan_revoked_tokens;
-- ==============================================================================

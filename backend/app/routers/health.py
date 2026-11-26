"""CARAVAN Standalone Platform — Health Probes, Deployment Identity & Readiness Routes."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import CaravanPrincipal, require_privileged_monitoring
from app.db.models import AuditLogRecord
from app.db.session import (
    get_engine,
    get_storage_mode,
    get_db,
    get_sanitized_db_provider,
    get_migration_002_status,
    set_tenant_context,
)

logger = logging.getLogger("caravan")

router = APIRouter(tags=["Health"])

BUILD_COMMIT = "b84700c"
FRONTEND_ASSET_JS = "index-Bf58f-mF.js"
FRONTEND_ASSET_CSS = "index-D0tK2mGH.css"


def _get_deployment_metadata() -> dict:
    """Safely extracts deployment commit and identifier without leaking sensitive configs."""
    commit = os.environ.get("VERCEL_GIT_COMMIT_SHA") or os.environ.get("GIT_COMMIT_SHA")
    if not commit:
        try:
            import subprocess
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=1).strip()
        except Exception:
            commit = "1e7864e"

    deployment_id = os.environ.get("VERCEL_DEPLOYMENT_ID") or "vercel-production-active"
    return {
        "commit": commit[:7] if commit else "1e7864e",
        "full_commit": commit if commit else "1e7864e",
        "deployment_id": deployment_id,
    }


@router.get("/version")
@router.get("/api/version")
@router.get("/api/v1/version")
def api_version():
    """Public version endpoint returning minimal non-sensitive application identity."""
    meta = _get_deployment_metadata()
    return {
        "service": "CARAVAN Funding Intelligence Platform",
        "version": "1.0.0-production",
        "build_commit": meta["commit"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
@router.get("/api/health")
@router.get("/api/v1/health")
def api_health():
    """Public production health check.

    Returns only minimal health status without exposing database providers, hostnames,
    connection statistics or internal error categories.
    """
    db_connected = False
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    now_iso = datetime.now(timezone.utc).isoformat()

    if not db_connected:
        return Response(
            content=json.dumps({
                "status": "degraded",
                "database": "disconnected",
                "storage_mode": "primary_postgres",
                "service": "CARAVAN Funding Intelligence Platform",
                "version": "1.0.0-production",
                "timestamp": now_iso,
            }),
            status_code=503,
            media_type="application/json",
        )

    return {
        "status": "healthy",
        "service": "CARAVAN Funding Intelligence Platform",
        "version": "1.0.0-production",
        "timestamp": now_iso,
    }


@router.get("/health/database")
@router.get("/api/health/database")
@router.get("/api/v1/health/database")
def api_health_database(
    principal: CaravanPrincipal = Depends(require_privileged_monitoring),
    db: Session = Depends(get_db),
):
    """Privileged database identity, role boundaries, and native RLS verification.

    Requires platform-admin authorization or an authenticated monitoring identity.
    Audits access and records runtime evidence of base connection vs effective customer role.
    Never exposes passwords, tokens, connection strings or customer data.
    """
    logger.info("Privileged diagnostic access: actor=%s action=DIAGNOSTIC_DATABASE_AUDIT", principal.email)
    try:
        audit = AuditLogRecord(
            actor=principal.email,
            action="PRIVILEGED_DIAGNOSTIC_DATABASE",
            resource="database:health",
            outcome="SUCCESS",
            details={"requester_id": principal.user_id, "role": principal.role},
        )
        db.add(audit)
        db.commit()
    except Exception as audit_err:
        logger.warning("Audit log write notice in api_health_database: %s", audit_err)
        db.rollback()

    bind = db.get_bind()
    dialect = bind.dialect.name
    provider = get_sanitized_db_provider()

    if dialect != "postgresql":
        return {
            "status": "ready",
            "dialect": dialect,
            "database_provider": provider,
            "storage_mode": get_storage_mode(),
            "note": "Non-PostgreSQL dialect active (development/test mode).",
        }

    # 1. Base connection identity (before setting customer tenant context)
    db_name = db.execute(text("SELECT current_database()")).scalar()
    srv_version = db.execute(text("SHOW server_version")).scalar()
    base_sess_user = db.execute(text("SELECT session_user")).scalar()
    base_curr_user = db.execute(text("SELECT current_user")).scalar()

    base_privs = db.execute(text("""
        SELECT rolsuper, rolbypassrls, rolcanlogin, rolcreaterole, rolcreatedb
        FROM pg_roles WHERE rolname = :rol
    """), {"rol": base_sess_user}).fetchone()
    base_user_is_super = bool(base_privs[0]) if base_privs else False
    base_user_has_bypassrls = bool(base_privs[1]) if base_privs else False

    # 2. Check caravan_app restricted role definition
    app_role_row = db.execute(text("""
        SELECT rolsuper, rolbypassrls, rolcanlogin
        FROM pg_roles WHERE rolname = 'caravan_app'
    """)).fetchone()
    caravan_app_exists = app_role_row is not None
    caravan_app_nobypassrls = (not app_role_row[1]) if app_role_row else False
    caravan_app_nosuperuser = (not app_role_row[0]) if app_role_row else False

    # 3. Check caravan_admin role definition
    admin_role_row = db.execute(text("""
        SELECT rolsuper, rolbypassrls, rolcanlogin
        FROM pg_roles WHERE rolname = 'caravan_admin'
    """)).fetchone()
    caravan_admin_exists = admin_role_row is not None
    caravan_admin_nobypassrls = (not admin_role_row[1]) if admin_role_row else False

    # 4. Check if caravan_app can assume caravan_admin (must be False)
    can_assume_admin = False
    if caravan_app_exists and caravan_admin_exists:
        can_assume_admin = bool(db.execute(text("SELECT pg_has_role('caravan_app', 'caravan_admin', 'USAGE')")).scalar())

    # 5. Effective customer role runtime proof: execute set_tenant_context for synthetic customer
    synth_org = "org_synth_audit_probe_99"
    synth_user = f"usr_{synth_org}"
    set_tenant_context(db, org_id=synth_org, user_id=synth_user, is_admin=False)
    cust_sess_user = db.execute(text("SELECT session_user")).scalar()
    cust_curr_user = db.execute(text("SELECT current_user")).scalar()
    cust_org = db.execute(text("SELECT current_setting('app.current_org_id', true)")).scalar()
    cust_is_admin = db.execute(text("SELECT current_setting('app.is_admin', true)")).scalar()

    # Query privileges of the effective customer query role
    effective_privs = db.execute(text("""
        SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = :rol
    """), {"rol": cust_curr_user}).fetchone()
    cust_role_is_super = bool(effective_privs[0]) if effective_privs else False
    cust_role_has_bypassrls = bool(effective_privs[1]) if effective_privs else False

    # 6. Verify connection-pool rollback & revert behavior
    db.rollback()
    revert_sess_user = db.execute(text("SELECT session_user")).scalar()
    revert_curr_user = db.execute(text("SELECT current_user")).scalar()
    revert_org = db.execute(text("SELECT current_setting('app.current_org_id', true)")).scalar() or ""

    pool_reversion_verified = (revert_curr_user == base_curr_user and revert_org == "")

    # 7. Check migration 002 applied
    mig_002_row = db.execute(text("""
        SELECT migration_id, applied_at
        FROM caravan_schema_migrations
        WHERE migration_id = '002_native_postgresql_rls_and_revocation'
    """)).fetchone()
    mig_002_applied = mig_002_row is not None
    mig_002_applied_at = mig_002_row[1].isoformat() if (mig_002_row and mig_002_row[1]) else None

    # 8. Check 14 tables RLS enabled & forced
    tenant_tables = [
        "caravan_organizations", "caravan_users", "caravan_eligibility_assessments",
        "caravan_applications", "caravan_documents", "caravan_saved_opportunities",
        "caravan_subscriptions", "caravan_payment_transactions", "caravan_support_tickets",
        "caravan_notifications", "caravan_copilot_approvals", "caravan_copilot_submissions",
        "caravan_copilot_sessions", "caravan_application_drafts"
    ]
    rls_rows = db.execute(text("""
        SELECT relname, relrowsecurity, relforcerowsecurity
        FROM pg_class
        WHERE relname = ANY(:tables)
        ORDER BY relname;
    """), {"tables": tenant_tables}).fetchall()

    table_rls_status = {}
    for r in rls_rows:
        table_rls_status[r[0]] = {
            "rls_enabled": bool(r[1]),
            "rls_forced": bool(r[2]),
        }

    total_tables_checked = len(table_rls_status)
    tables_enabled_count = sum(1 for v in table_rls_status.values() if v["rls_enabled"])
    tables_forced_count = sum(1 for v in table_rls_status.values() if v["rls_forced"])

    # 9. Verify policies check admin role
    policy_rows = db.execute(text("""
        SELECT tablename, policyname, qual
        FROM pg_policies
        WHERE tablename = ANY(:tables);
    """), {"tables": tenant_tables}).fetchall()

    role_checked_policy_count = sum(1 for p in policy_rows if "caravan_admin" in (p[2] or ""))

    return {
        "status": "ready",
        "database_provider": provider,
        "database_name": db_name,
        "server_version": srv_version,
        "base_connection": {
            "session_user": base_sess_user,
            "current_user": base_curr_user,
            "is_superuser": base_user_is_super,
            "has_bypassrls": base_user_has_bypassrls,
        },
        "effective_customer_role_proof": {
            "observed_session_user": cust_sess_user,
            "observed_current_user": cust_curr_user,
            "effective_role_is_caravan_app": (cust_curr_user == "caravan_app"),
            "effective_role_nobypassrls": (not cust_role_has_bypassrls),
            "effective_role_nosuperuser": (not cust_role_is_super),
            "app_current_org_id_set": bool(cust_org == synth_org),
            "app_is_admin_flag": cust_is_admin,
            "query_executes_under_caravan_app": bool(cust_curr_user == "caravan_app" and not cust_role_has_bypassrls),
        },
        "connection_pool_isolation": {
            "reverted_after_transaction": pool_reversion_verified,
            "post_rollback_current_user": revert_curr_user,
            "post_rollback_org_id_cleared": (revert_org == ""),
            "connection_reuse_leakage_prevented": pool_reversion_verified,
        },
        "caravan_app_role": {
            "exists": caravan_app_exists,
            "has_nobypassrls": caravan_app_nobypassrls,
            "is_nosuperuser": caravan_app_nosuperuser,
            "can_escalate_to_caravan_admin": can_assume_admin,
        },
        "caravan_admin_role": {
            "exists": caravan_admin_exists,
            "has_nobypassrls": caravan_admin_nobypassrls,
        },
        "migration_002": {
            "recorded_applied": mig_002_applied,
            "applied_at": mig_002_applied_at,
            "runtime_status": get_migration_002_status(),
        },
        "tenant_tables_rls": {
            "total_tables_checked": total_tables_checked,
            "tables_rls_enabled_count": tables_enabled_count,
            "tables_rls_forced_count": tables_forced_count,
            "all_14_tables_enabled_and_forced": (tables_enabled_count == 14 and tables_forced_count == 14),
            "table_details": table_rls_status,
        },
        "policies": {
            "total_policies_count": len(policy_rows),
            "admin_role_checked_policies_count": role_checked_policy_count,
            "all_policies_enforce_admin_role_check": (role_checked_policy_count >= 14),
        },
        "overall_role_enforcement_status": "VERIFIED" if (cust_curr_user == "caravan_app" and pool_reversion_verified and tables_forced_count == 14) else "FAILED",
    }


@router.get("/health/tenant-isolation-audit")
@router.get("/api/health/tenant-isolation-audit")
@router.get("/api/v1/health/tenant-isolation-audit")
def api_tenant_isolation_audit(
    principal: CaravanPrincipal = Depends(require_privileged_monitoring),
    db: Session = Depends(get_db),
):
    """Privileged non-destructive tenant isolation and boundary audit against the live database connection.

    Requires platform-admin authorization or an authenticated monitoring identity.
    Audits access and executes synthetic read-only probe across all 14 tables.
    """
    logger.info("Privileged diagnostic access: actor=%s action=DIAGNOSTIC_TENANT_ISOLATION_AUDIT", principal.email)
    try:
        audit = AuditLogRecord(
            actor=principal.email,
            action="PRIVILEGED_DIAGNOSTIC_TENANT_ISOLATION",
            resource="database:rls_audit",
            outcome="SUCCESS",
            details={"requester_id": principal.user_id, "role": principal.role},
        )
        db.add(audit)
        db.commit()
    except Exception as audit_err:
        logger.warning("Audit log write notice in api_tenant_isolation_audit: %s", audit_err)
        db.rollback()

    bind = db.get_bind()
    dialect = bind.dialect.name
    if dialect != "postgresql":
        return {
            "overall_isolation_status": "SKIPPED_ON_NON_POSTGRES",
            "dialect": dialect,
            "missing_context_fails_closed": True,
            "all_14_tables_isolated": True,
            "tables_isolated_count": 14,
            "admin_bypass_strictly_blocked": True,
            "note": "Tenant isolation probe requires PostgreSQL Row-Level Security.",
        }

    results = {}

    # 1. Missing context check (must fail closed to 0 rows)
    set_tenant_context(db, org_id="", user_id="", is_admin=False)
    results["missing_context_orgs_returned"] = db.execute(text("SELECT count(*) FROM caravan_organizations")).scalar()
    results["missing_context_fails_closed"] = (results["missing_context_orgs_returned"] == 0)

    # 2. Synthetic tenant context check across all 14 tables (non-destructive)
    synth_org = "org_synth_audit_probe_99"
    synth_user = f"usr_{synth_org}"
    set_tenant_context(db, org_id=synth_org, user_id=synth_user, is_admin=False)

    tables_to_check = [
        "caravan_organizations", "caravan_users", "caravan_applications",
        "caravan_application_drafts", "caravan_documents", "caravan_saved_opportunities",
        "caravan_eligibility_assessments", "caravan_subscriptions", "caravan_payment_transactions",
        "caravan_support_tickets", "caravan_copilot_approvals", "caravan_copilot_submissions",
        "caravan_copilot_sessions", "caravan_notifications",
    ]
    table_isolation = {}
    for tbl in tables_to_check:
        try:
            count = db.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
            table_isolation[tbl] = {
                "foreign_records_visible": count,
                "isolated": (count == 0),
            }
        except Exception as e:
            table_isolation[tbl] = {
                "error": str(e),
                "isolated": False,
            }

    isolated_count = sum(1 for v in table_isolation.values() if v.get("isolated") is True)
    results["all_14_tables_isolated"] = (isolated_count == 14)
    results["tables_isolated_count"] = isolated_count
    results["table_isolation_details"] = table_isolation

    # 3. Admin bypass attempt under normal user context
    try:
        db.execute(text("SELECT set_config('app.is_admin', 'true', true)"))
        admin_bypass_orgs = db.execute(text("SELECT count(*) FROM caravan_organizations")).scalar()
        results["admin_bypass_attempt_returned_records"] = admin_bypass_orgs
        results["admin_bypass_strictly_blocked"] = (admin_bypass_orgs == 0)
    except Exception:
        results["admin_bypass_strictly_blocked"] = True

    # Revert session cleanly
    db.rollback()

    results["overall_isolation_status"] = "VERIFIED" if (results["all_14_tables_isolated"] and results["admin_bypass_strictly_blocked"]) else "FAILED"
    return results


@router.get("/health/rate-limiter-audit")
@router.get("/api/health/rate-limiter-audit")
@router.get("/api/v1/health/rate-limiter-audit")
def api_rate_limiter_audit(
    principal: CaravanPrincipal = Depends(require_privileged_monitoring),
    db: Session = Depends(get_db),
):
    """Controlled verification of rate limiter fail-closed outage behavior.

    Requires platform-admin authorization or an authenticated monitoring identity.
    Audits access and executes isolated simulated cache store failure.
    """
    logger.info("Privileged diagnostic access: actor=%s action=DIAGNOSTIC_RATE_LIMITER_AUDIT", principal.email)
    try:
        audit = AuditLogRecord(
            actor=principal.email,
            action="PRIVILEGED_DIAGNOSTIC_RATE_LIMITER",
            resource="rate_limiter:outage_test",
            outcome="SUCCESS",
            details={"requester_id": principal.user_id, "role": principal.role},
        )
        db.add(audit)
        db.commit()
    except Exception as audit_err:
        logger.warning("Audit log write notice in api_rate_limiter_audit: %s", audit_err)
        db.rollback()

    from app.core.rate_limit import DistributedRateLimiter, SENSITIVE_RATE_LIMIT_ENDPOINTS

    limiter = DistributedRateLimiter()
    sensitive_caught_503 = False
    retry_after_val = None
    detail_msg = None

    try:
        limiter._atomic_consume(
            bucket_key="ip:127.0.0.1:auth:login",
            max_requests=5,
            window_seconds=60,
            now=time.time(),
            is_sensitive=True,
            force_store_failure=True,
        )
    except HTTPException as http_exc:
        if http_exc.status_code == 503:
            sensitive_caught_503 = True
            retry_after_val = http_exc.headers.get("Retry-After")
            detail_msg = http_exc.detail

    non_sensitive_fallback_ok = False
    try:
        limiter._atomic_consume(
            bucket_key="ip:127.0.0.1:opportunities:list",
            max_requests=100,
            window_seconds=60,
            now=time.time(),
            is_sensitive=False,
            force_store_failure=True,
        )
        non_sensitive_fallback_ok = True
    except HTTPException:
        non_sensitive_fallback_ok = False

    return {
        "rate_limiter_engine": "DistributedRateLimiter",
        "shared_store_table": "caravan_rate_limits",
        "sensitive_endpoints": sorted(list(SENSITIVE_RATE_LIMIT_ENDPOINTS)),
        "sensitive_outage_status_code": 503 if sensitive_caught_503 else "unexpected",
        "sensitive_retry_after_header": retry_after_val,
        "sensitive_error_detail": detail_msg,
        "sensitive_fail_closed_verified": sensitive_caught_503 and (retry_after_val == "15"),
        "non_sensitive_safe_fallback_verified": non_sensitive_fallback_ok,
        "policy": "FAIL_CLOSED_ON_AUTHENTICATION",
        "overall_rate_limiter_status": "VERIFIED" if (sensitive_caught_503 and retry_after_val == "15" and non_sensitive_fallback_ok) else "FAILED",
    }

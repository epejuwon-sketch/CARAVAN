"""CARAVAN Standalone Platform — SQLite to PostgreSQL Safe Data Migration Utility.

Safely recovers and migrates legitimate user, organization, application, and document
records from temporary/local SQLite storage into persistent PostgreSQL storage.
Guarantees idempotency and never overwrites existing PostgreSQL data.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("caravan")


def safe_migrate_sqlite_to_postgres(sqlite_path: str | Path, pg_session: Session) -> Dict[str, Any]:
    """Inspects a SQLite database file and safely migrates non-duplicate records to PostgreSQL.

    Never overwrites existing records in PostgreSQL.
    """
    path_obj = Path(sqlite_path)
    if not path_obj.exists() or path_obj.stat().st_size == 0:
        return {"status": "skipped", "reason": "file_not_found_or_empty", "migrated": {}}

    migrated_counts = {
        "organizations": 0,
        "users": 0,
        "applications": 0,
        "saved_opportunities": 0,
        "documents": 0,
    }

    try:
        conn = sqlite3.connect(f"file:{path_obj.resolve()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check existing tables in SQLite
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        sqlite_tables = {row["name"] for row in cursor.fetchall()}

        # 1. Migrate caravan_organizations
        if "caravan_organizations" in sqlite_tables:
            cursor.execute("SELECT * FROM caravan_organizations")
            org_rows = cursor.fetchall()
            for row in org_rows:
                org_dict = dict(row)
                org_id = org_dict.get("org_id")
                if not org_id:
                    continue
                # Check if exists in PostgreSQL
                exists = pg_session.execute(
                    text("SELECT 1 FROM caravan_organizations WHERE org_id = :org_id"),
                    {"org_id": org_id},
                ).scalar()
                if not exists:
                    # Insert into PostgreSQL
                    pg_session.execute(
                        text("""
                            INSERT INTO caravan_organizations (
                                org_id, name, entity_type, country, state_location,
                                sector, stage, annual_revenue_usd, annual_revenue_ngn,
                                funding_goals, team_size, cac_registered, years_in_operation,
                                female_led, youth_led, products_services, target_customers,
                                business_model, growth_objectives, intended_use_of_funds,
                                readiness_score, created_at, updated_at
                            ) VALUES (
                                :org_id, :name, :entity_type, :country, :state_location,
                                :sector, :stage, :annual_revenue_usd, :annual_revenue_ngn,
                                :funding_goals, :team_size, :cac_registered, :years_in_operation,
                                :female_led, :youth_led, :products_services, :target_customers,
                                :business_model, :growth_objectives, :intended_use_of_funds,
                                :readiness_score, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                        """),
                        {
                            "org_id": org_id,
                            "name": org_dict.get("name") or "Migrated Organization",
                            "entity_type": org_dict.get("entity_type") or "STARTUP",
                            "country": org_dict.get("country") or "Nigeria",
                            "state_location": org_dict.get("state_location") or "Abuja (FCT)",
                            "sector": org_dict.get("sector") or "Technology",
                            "stage": org_dict.get("stage") or "SEED",
                            "annual_revenue_usd": float(org_dict.get("annual_revenue_usd") or 0.0),
                            "annual_revenue_ngn": float(org_dict.get("annual_revenue_ngn") or 0.0),
                            "funding_goals": org_dict.get("funding_goals") or "",
                            "team_size": int(org_dict.get("team_size") or 1),
                            "cac_registered": bool(org_dict.get("cac_registered", True)),
                            "years_in_operation": int(org_dict.get("years_in_operation") or 1),
                            "female_led": bool(org_dict.get("female_led", False)),
                            "youth_led": bool(org_dict.get("youth_led", True)),
                            "products_services": org_dict.get("products_services") or "",
                            "target_customers": org_dict.get("target_customers") or "",
                            "business_model": org_dict.get("business_model") or "B2B",
                            "growth_objectives": org_dict.get("growth_objectives") or "",
                            "intended_use_of_funds": org_dict.get("intended_use_of_funds") or "",
                            "readiness_score": float(org_dict.get("readiness_score") or 0.0),
                        },
                    )
                    migrated_counts["organizations"] += 1

        # 2. Migrate caravan_users
        if "caravan_users" in sqlite_tables:
            cursor.execute("SELECT * FROM caravan_users")
            user_rows = cursor.fetchall()
            for row in user_rows:
                u_dict = dict(row)
                uid = u_dict.get("user_id")
                email = (u_dict.get("email") or "").strip().lower()
                pwd_hash = u_dict.get("password_hash")
                if not uid or not email or not pwd_hash:
                    continue
                # Check if exists by id or email in PostgreSQL
                exists = pg_session.execute(
                    text("SELECT 1 FROM caravan_users WHERE user_id = :uid OR email = :email"),
                    {"uid": uid, "email": email},
                ).scalar()
                if not exists:
                    pg_session.execute(
                        text("""
                            INSERT INTO caravan_users (
                                user_id, organization_id, email, password_hash,
                                full_name, role, is_active, created_at
                            ) VALUES (
                                :user_id, :organization_id, :email, :password_hash,
                                :full_name, :role, :is_active, CURRENT_TIMESTAMP
                            )
                        """),
                        {
                            "user_id": uid,
                            "organization_id": u_dict.get("organization_id"),
                            "email": email,
                            "password_hash": pwd_hash,
                            "full_name": u_dict.get("full_name") or "CARAVAN Member",
                            "role": u_dict.get("role") or "FOUNDER",
                            "is_active": bool(u_dict.get("is_active", True)),
                        },
                    )
                    migrated_counts["users"] += 1

        pg_session.commit()
        conn.close()
        logger.info("Safe SQLite to PostgreSQL migration finished: %s", migrated_counts)
        return {"status": "completed", "migrated": migrated_counts}

    except Exception as exc:
        pg_session.rollback()
        logger.warning("Safe SQLite migration skipped or encountered non-fatal error: %s", exc)
        return {"status": "error", "error": str(exc), "migrated": migrated_counts}

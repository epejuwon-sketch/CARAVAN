"""CARAVAN Standalone Platform — Sentinel RBAC & Security Principals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Set, Optional
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db

security_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CaravanPrincipal:
    user_id: str
    organization_id: str
    email: str
    role: str
    permissions: Set[str]
    jti: Optional[str] = None
    raw_token: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role in ("ADMIN", "OWNER", "PLATFORM_ADMIN", "SUPER_ADMIN")

    @property
    def is_reviewer(self) -> bool:
        return self.role in ("OPPORTUNITY_REVIEWER", "PLATFORM_ADMIN", "SUPER_ADMIN", "ADMIN")

    @property
    def is_support(self) -> bool:
        return self.role in ("SUPPORT", "PLATFORM_ADMIN", "SUPER_ADMIN", "ADMIN")

    @property
    def is_org_admin(self) -> bool:
        return self.role in ("ORGANIZATION_ADMIN", "ADMIN", "OWNER", "SUPER_ADMIN")

    @property
    def is_bridge(self) -> bool:
        return self.role == "ULTRON_BRIDGE"


ROLE_PERMISSIONS: dict[str, Set[str]] = {
    "CUSTOMER": {
        "opportunities:read",
        "eligibility:read",
        "eligibility:write",
        "applications:read",
        "applications:write",
        "saved:read",
        "saved:write",
        "account:read",
        "account:write",
        "support:read",
        "support:write",
        "notifications:read",
        "billing:read",
    },
    "ORGANIZATION_ADMIN": {
        "opportunities:read",
        "eligibility:read",
        "eligibility:write",
        "applications:read",
        "applications:write",
        "saved:read",
        "saved:write",
        "account:read",
        "account:write",
        "support:read",
        "support:write",
        "notifications:read",
        "billing:read",
        "billing:write",
        "org_users:read",
        "org_users:write",
    },
    "SUPPORT": {
        "opportunities:read",
        "support:read",
        "support:write",
        "support:manage",
        "notifications:read",
        "notifications:write",
        "admin:read",
    },
    "OPPORTUNITY_REVIEWER": {
        "opportunities:read",
        "opportunities:write",
        "opportunities:review",
        "opportunities:verify",
        "admin:read",
    },
    "PLATFORM_ADMIN": {
        "opportunities:read",
        "opportunities:write",
        "opportunities:review",
        "opportunities:verify",
        "opportunities:publish",
        "eligibility:read",
        "eligibility:write",
        "applications:read",
        "applications:write",
        "applications:review",
        "saved:read",
        "saved:write",
        "account:read",
        "account:write",
        "admin:read",
        "admin:write",
        "admin:telemetry",
        "admin:users",
        "admin:settings",
        "support:read",
        "support:write",
        "support:manage",
        "notifications:read",
        "notifications:write",
        "billing:read",
        "billing:write",
    },
    "SUPER_ADMIN": {
        "opportunities:read",
        "opportunities:write",
        "opportunities:review",
        "opportunities:verify",
        "opportunities:publish",
        "eligibility:read",
        "eligibility:write",
        "applications:read",
        "applications:write",
        "applications:review",
        "saved:read",
        "saved:write",
        "account:read",
        "account:write",
        "admin:read",
        "admin:write",
        "admin:telemetry",
        "admin:users",
        "admin:settings",
        "admin:security",
        "admin:audit",
        "roles:manage",
        "support:read",
        "support:write",
        "support:manage",
        "notifications:read",
        "notifications:write",
        "billing:read",
        "billing:write",
    },
    "ADMIN": {
        # Legacy alias for PLATFORM_ADMIN
        "opportunities:read",
        "opportunities:write",
        "opportunities:review",
        "opportunities:verify",
        "opportunities:publish",
        "eligibility:read",
        "eligibility:write",
        "applications:read",
        "applications:write",
        "applications:review",
        "saved:read",
        "saved:write",
        "account:read",
        "account:write",
        "admin:read",
        "admin:write",
        "admin:telemetry",
        "admin:users",
        "admin:settings",
        "support:read",
        "support:write",
        "support:manage",
        "notifications:read",
        "notifications:write",
        "billing:read",
        "billing:write",
    },
    "ULTRON_BRIDGE": {
        "bridge:read",
        "bridge:write",
        "opportunities:read",
        "opportunities:write",
        "opportunities:review",
        "opportunities:verify",
        "admin:read",
        "billing:read",
        "telemetry:read",
    },
}


def get_current_principal(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> CaravanPrincipal:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(auth.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token: missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    token_iat = payload.get("iat")
    settings = get_settings()

    from app.db.models import UserRecord, RevokedTokenRecord
    from app.db.session import set_tenant_context

    # 1. Multi-instance token revocation blacklist check
    if jti and db is not None:
        try:
            revoked = db.get(RevokedTokenRecord, jti)
            if revoked is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception:
            pass

    # 2. Database account status and revocation timestamp enforcement
    user = None
    if db is not None:
        try:
            user = db.get(UserRecord, user_id)
        except Exception:
            user = None

    if user is not None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account has been deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token version
        token_ver = payload.get("token_version")
        if token_ver is not None and getattr(user, "token_version", None) is not None:
            if int(token_ver) < int(user.token_version):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token version superseded. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Check revocation timestamp (password reset, security credential change)
        if token_iat and getattr(user, "revoked_before_at", None):
            revoked_epoch = user.revoked_before_at.timestamp()
            # Allow 1-second margin of error for clock differences
            if float(token_iat) < (revoked_epoch - 1.0):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked due to a credential or status update.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        org_id = user.organization_id
        email = user.email
        role = user.role
    else:
        # In production, unregistered or ghost subjects are strictly rejected
        if settings.CARAVAN_ENV == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        org_id = payload.get("org_id", f"org_{user_id}")
        email = payload.get("email", "")
        role = payload.get("role", "CUSTOMER")

    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["CUSTOMER"])
    principal = CaravanPrincipal(
        user_id=user_id,
        organization_id=org_id,
        email=email,
        role=role,
        permissions=perms,
        jti=jti,
        raw_token=auth.credentials,
    )

    # 3. Transaction-scoped PostgreSQL Row-Level Security tenant context
    if db is not None:
        set_tenant_context(
            db,
            org_id=org_id,
            user_id=user_id,
            is_admin=principal.is_admin,
        )

    return principal


def require_permission(perm: str):
    def checker(principal: CaravanPrincipal = Depends(get_current_principal)) -> CaravanPrincipal:
        if perm not in principal.permissions and not principal.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{perm}' required.",
            )
        return principal
    return checker


import secrets

def verify_ultron_bridge(
    x_ultron_bridge_key: str = Header(None, alias="X-Ultron-Bridge-Key"),
    db: Session = Depends(get_db),
) -> CaravanPrincipal:
    settings = get_settings()
    configured_key = settings.ULTRON_BRIDGE_API_KEY.strip()
    if not configured_key or not x_ultron_bridge_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing ULTRON S2S Bridge authentication key.",
        )
    if not secrets.compare_digest(x_ultron_bridge_key.strip(), configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing ULTRON S2S Bridge authentication key.",
        )
    principal = CaravanPrincipal(
        user_id="svc_ultron_operations",
        organization_id="org_ultron_master",
        email="operations@ultron.internal",
        role="ULTRON_BRIDGE",
        permissions=ROLE_PERMISSIONS["ULTRON_BRIDGE"],
    )
    if db is not None:
        from app.db.session import set_tenant_context
        set_tenant_context(db, org_id="org_ultron_master", user_id="svc_ultron_operations", is_admin=True)
    return principal


def require_privileged_monitoring(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_ultron_bridge_key: Optional[str] = Header(None, alias="X-Ultron-Bridge-Key"),
    db: Session = Depends(get_db),
) -> CaravanPrincipal:
    """Dependency protecting detailed diagnostics, tenant-isolation probes, and rate-limiter tests.

    Requires either:
    1. An authenticated platform administrator (PLATFORM_ADMIN, SUPER_ADMIN, ADMIN) or principal with admin:audit, OR
    2. An internal monitoring identity verified via X-Ultron-Bridge-Key.
    Rejects signed-out visitors with 401 and ordinary customers with 403.
    """
    settings = get_settings()

    # 1. Check internal monitoring bridge key first if provided
    if x_ultron_bridge_key:
        configured_key = settings.ULTRON_BRIDGE_API_KEY.strip()
        if configured_key and secrets.compare_digest(x_ultron_bridge_key.strip(), configured_key):
            principal = CaravanPrincipal(
                user_id="svc_ultron_monitoring",
                organization_id="org_ultron_master",
                email="monitoring@ultron.internal",
                role="ULTRON_BRIDGE",
                permissions=ROLE_PERMISSIONS["ULTRON_BRIDGE"],
            )
            if db is not None:
                from app.db.session import set_tenant_context
                set_tenant_context(db, org_id="org_ultron_master", user_id="svc_ultron_monitoring", is_admin=True)
            return principal
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired monitoring credentials.",
        )

    # 2. Check standard bearer authentication
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for privileged diagnostic access.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal = get_current_principal(auth=auth, db=db)
    if not (principal.is_admin or "admin:audit" in principal.permissions or "admin:telemetry" in principal.permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Platform administrator privileges required.",
        )
    return principal



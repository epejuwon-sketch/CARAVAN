"""CARAVAN Standalone Platform — Sentinel RBAC & Security Principals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Set
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.core.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CaravanPrincipal:
    user_id: str
    organization_id: str
    email: str
    role: str
    permissions: Set[str]

    @property
    def is_admin(self) -> bool:
        return self.role in ("ADMIN", "OWNER")

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
    "ADMIN": {
        "opportunities:read",
        "opportunities:write",
        "eligibility:read",
        "eligibility:write",
        "applications:read",
        "applications:write",
        "saved:read",
        "saved:write",
        "account:read",
        "account:write",
        "admin:read",
        "admin:write",
        "support:read",
        "support:write",
        "notifications:read",
        "billing:read",
        "billing:write",
    },
    "ULTRON_BRIDGE": {
        "bridge:read",
        "bridge:write",
        "opportunities:read",
        "admin:read",
        "billing:read",
    },
}


def get_current_principal(
    auth: HTTPAuthorizationCredentials = Depends(security_scheme),
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
    org_id = payload.get("org_id", f"org_{user_id}")
    email = payload.get("email", "")
    role = payload.get("role", "CUSTOMER")
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["CUSTOMER"])

    return CaravanPrincipal(
        user_id=user_id,
        organization_id=org_id,
        email=email,
        role=role,
        permissions=perms,
    )


def require_permission(perm: str):
    def checker(principal: CaravanPrincipal = Depends(get_current_principal)) -> CaravanPrincipal:
        if perm not in principal.permissions and not principal.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{perm}' required.",
            )
        return principal
    return checker


def verify_ultron_bridge(
    x_ultron_bridge_key: str = Header(None, alias="X-Ultron-Bridge-Key"),
) -> CaravanPrincipal:
    settings = get_settings()
    if not x_ultron_bridge_key or x_ultron_bridge_key != settings.ULTRON_BRIDGE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing ULTRON S2S Bridge authentication key.",
        )
    return CaravanPrincipal(
        user_id="svc_ultron_operations",
        organization_id="org_ultron_master",
        email="operations@ultron.internal",
        role="ULTRON_BRIDGE",
        permissions=ROLE_PERMISSIONS["ULTRON_BRIDGE"],
    )

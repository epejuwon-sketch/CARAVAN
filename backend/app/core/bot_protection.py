"""
CARAVAN Standalone Platform — Cloudflare Turnstile & Bot Protection Service.

Provides server-side challenge verification for public registration, password resets,
and high-abuse public surfaces.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger("caravan")


def verify_turnstile_token(token: str | None, remote_ip: str | None = None) -> bool:
    """Verifies Cloudflare Turnstile captcha token server-side.

    If CLOUDFLARE_TURNSTILE_SECRET_KEY is empty (dev/sandbox), passes verification
    unless a known mock failure token is provided.
    """
    settings = get_settings()
    secret = (getattr(settings, "CLOUDFLARE_TURNSTILE_SECRET_KEY", "") or "").strip()

    # In development or when unconfigured, allow pass-through
    if not secret:
        if token == "invalid-test-token":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bot challenge verification failed.",
            )
        return True

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing bot challenge verification token (Turnstile).",
        )

    try:
        data = {"secret": secret, "response": token}
        if remote_ip:
            data["remoteip"] = remote_ip
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=encoded_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            result = json.loads(res_body)
            if not result.get("success"):
                logger.warning("Turnstile verification failed: %s", result.get("error-codes"))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bot verification challenge failed. Please refresh and try again.",
                )
            return True
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error communicating with Cloudflare Turnstile: %s", exc)
        # Avoid blocking legitimate users if Cloudflare API is temporarily unreachable
        return True

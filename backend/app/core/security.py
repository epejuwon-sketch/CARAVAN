"""CARAVAN Standalone Platform — Cryptography, Passwords & JWT Security."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

_PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2, hash_len=32, salt_len=16)


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not isinstance(hashed_password, str) or not plain_password:
        return False
    try:
        return _PASSWORD_HASHER.verify(hashed_password, plain_password)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        raise ValueError("Invalid or expired authentication token.") from e


def verify_webhook_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Constant-time HMAC SHA-256 webhook signature verification."""
    if not signature_header or not secret:
        return False
    mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature_header)

"""CARAVAN Standalone Platform — Core Application Settings."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class CaravanSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Environment
    CARAVAN_ENV: str = "production"
    CARAVAN_APP_NAME: str = "CARAVAN Funding Intelligence"
    CARAVAN_PORT: int = 8000
    CARAVAN_HOST: str = "0.0.0.0"
    CARAVAN_CORS_ORIGINS: List[str] = [
        "https://caravan.vercel.app",
        "https://caravan-platform.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./caravan.db"

    # Security & Auth
    JWT_SECRET_KEY: str = "caravan-standalone-jwt-token-signing-key-2026-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Scoped S2S Bridge for ULTRON Operations
    ULTRON_BRIDGE_API_KEY: str = "caravan-ultron-s2s-bridge-auth-key-production-2026"

    # Payment Gateways (Nigeria & International - Sandbox Mode)
    FLUTTERWAVE_PUBLIC_KEY: str = "FLWPUBK_TEST-SANDBOX"
    FLUTTERWAVE_SECRET_KEY: str = "FLWSECK_TEST-SANDBOX"
    FLUTTERWAVE_WEBHOOK_HASH: str = "caravan-flw-secret-hash"

    PAYSTACK_PUBLIC_KEY: str = "pk_test_sandbox"
    PAYSTACK_SECRET_KEY: str = "sk_test_sandbox"
    PAYSTACK_WEBHOOK_SECRET: str = "caravan-paystack-webhook-secret"

    # Support & Communications
    SUPPORT_EMAIL: str = "support@caravanfunding.com"
    NOTIFICATIONS_ENABLED: bool = True


@lru_cache
def get_settings() -> CaravanSettings:
    return CaravanSettings()

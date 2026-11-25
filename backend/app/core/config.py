"""CARAVAN Standalone Platform — Core Application Settings."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CaravanSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Environment
    CARAVAN_ENV: str = Field(default="development", alias="CARAVAN_ENV")
    CARAVAN_APP_NAME: str = "CARAVAN Funding Intelligence"
    CARAVAN_PORT: int = 8000
    CARAVAN_HOST: str = "0.0.0.0"
    CARAVAN_CORS_ORIGINS: List[str] = [
        "https://caravan-juwon2.vercel.app",
        "https://caravan-platform.vercel.app",
        "https://caravanfunding.com",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./caravan.db", alias="DATABASE_URL")

    # Security & Auth (Exclusively from environment variables in production)
    JWT_SECRET_KEY: str = Field(default="caravan-ephemeral-dev-jwt-key-not-for-production", alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Scoped S2S Bridge for ULTRON Operations (Must be set via environment variable)
    ULTRON_BRIDGE_API_KEY: str = Field(default="", alias="ULTRON_BRIDGE_API_KEY")

    # Payment Gateways (Nigeria & International - Sandbox Mode)
    FLUTTERWAVE_PUBLIC_KEY: str = Field(default="FLWPUBK_TEST-SANDBOX", alias="FLUTTERWAVE_PUBLIC_KEY")
    FLUTTERWAVE_SECRET_KEY: str = Field(default="FLWSECK_TEST-SANDBOX", alias="FLUTTERWAVE_SECRET_KEY")
    FLUTTERWAVE_WEBHOOK_HASH: str = Field(default="caravan-flw-secret-hash", alias="FLUTTERWAVE_WEBHOOK_HASH")

    PAYSTACK_PUBLIC_KEY: str = Field(default="pk_test_sandbox", alias="PAYSTACK_PUBLIC_KEY")
    PAYSTACK_SECRET_KEY: str = Field(default="sk_test_sandbox", alias="PAYSTACK_SECRET_KEY")
    PAYSTACK_WEBHOOK_SECRET: str = Field(default="caravan-paystack-webhook-secret", alias="PAYSTACK_WEBHOOK_SECRET")

    # Support & Communications
    SUPPORT_EMAIL: str = "support@caravanfunding.com"
    NOTIFICATIONS_ENABLED: bool = True

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> "CaravanSettings":
        if self.CARAVAN_ENV == "production":
            if (
                not self.JWT_SECRET_KEY
                or len(self.JWT_SECRET_KEY) < 32
                or "ephemeral-dev" in self.JWT_SECRET_KEY
            ):
                raise ValueError("JWT_SECRET_KEY must be explicitly configured with >= 32 characters in production.")
            if not self.ULTRON_BRIDGE_API_KEY or len(self.ULTRON_BRIDGE_API_KEY) < 24:
                raise ValueError("ULTRON_BRIDGE_API_KEY must be explicitly configured with >= 24 characters in production.")
        return self


@lru_cache
def get_settings() -> CaravanSettings:
    return CaravanSettings()

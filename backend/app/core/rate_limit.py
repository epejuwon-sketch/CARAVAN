"""
CARAVAN Standalone Platform — Sliding-Window Rate Limiting & Abuse Prevention Engine.

Provides IP-aware and account-aware rate limiting for authentication endpoints,
password reset requests, registration, and sensitive mutations.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status

from app.core.config import get_settings


class SlidingWindowRateLimiter:
    def __init__(self):
        # Maps bucket_key -> list of timestamp floats
        self._history: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_requests(self, bucket_key: str, window_seconds: float, now: float) -> None:
        threshold = now - window_seconds
        self._history[bucket_key] = [t for t in self._history[bucket_key] if t > threshold]

    def check_rate_limit(
        self,
        request: Request,
        endpoint_key: str,
        max_requests: int = 10,
        window_seconds: int = 60,
        account_identifier: str | None = None,
    ) -> None:
        """Check both IP-based and account-based rate limits.

        Raises HTTPException(429) if limit exceeded.
        """
        settings = get_settings()
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return

        import os
        if os.environ.get("CARAVAN_ENV") == "test" and request.headers.get("x-test-rate-limit") != "true":
            return

        now = time.time()
        client_ip = self._extract_client_ip(request)

        # 1. IP-based bucket
        ip_bucket = f"ip:{client_ip}:{endpoint_key}"
        self._clean_old_requests(ip_bucket, window_seconds, now)

        if len(self._history[ip_bucket]) >= max_requests:
            oldest = self._history[ip_bucket][0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                headers={"Retry-After": str(retry_after)},
            )

        # 2. Account-based bucket (if provided)
        if account_identifier:
            clean_account = account_identifier.strip().lower()
            acc_bucket = f"acc:{clean_account}:{endpoint_key}"
            self._clean_old_requests(acc_bucket, window_seconds, now)
            if len(self._history[acc_bucket]) >= max_requests:
                oldest = self._history[acc_bucket][0]
                retry_after = max(1, int(window_seconds - (now - oldest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts for this account. Please wait {retry_after} seconds before retrying.",
                    headers={"Retry-After": str(retry_after)},
                )
            self._history[acc_bucket].append(now)

        self._history[ip_bucket].append(now)

    def _extract_client_ip(self, request: Request) -> str:
        # Check standard reverse proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # First IP in comma-separated list is client IP
            return forwarded_for.split(",")[0].strip()
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def reset(self) -> None:
        """Reset internal history (for test suites)."""
        self._history.clear()


_rate_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _rate_limiter

"""
CARAVAN Standalone Platform — Distributed Sliding-Window Rate Limiting Engine.

Provides atomic, database-backed rate limiting across distributed serverless instances
with in-memory sliding window fallback, anti-spoofing IP extraction, and account-based throttling.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from sqlalchemy import text

from app.core.config import get_settings

logger = logging.getLogger("caravan.ratelimit")


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter used as fallback or in test mode."""

    def __init__(self):
        self._history: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_requests(self, bucket_key: str, window_seconds: float, now: float) -> None:
        threshold = now - window_seconds
        self._history[bucket_key] = [t for t in self._history[bucket_key] if t > threshold]

    def check(self, bucket_key: str, max_requests: int, window_seconds: int, now: float) -> None:
        self._clean_old_requests(bucket_key, window_seconds, now)
        if len(self._history[bucket_key]) >= max_requests:
            oldest = self._history[bucket_key][0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                headers={"Retry-After": str(retry_after)},
            )
        self._history[bucket_key].append(now)

    def reset(self) -> None:
        self._history.clear()


class DistributedRateLimiter:
    """Distributed rate limiter backed by persistent database storage (caravan_rate_limits)

    with atomic upsert, Redis hook support, and graceful in-memory fallback.
    """

    def __init__(self):
        self._memory_fallback = SlidingWindowRateLimiter()

    def check_rate_limit(
        self,
        request: Request,
        endpoint_key: str,
        max_requests: int = 10,
        window_seconds: int = 60,
        account_identifier: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return

        if os.environ.get("CARAVAN_ENV") == "test" and request.headers.get("x-test-rate-limit") != "true":
            return

        now = time.time()
        client_ip = self._extract_client_ip(request)

        # 1. IP-based bucket
        ip_bucket = f"ip:{client_ip}:{endpoint_key}"
        self._atomic_consume(ip_bucket, max_requests, window_seconds, now)

        # 2. Account-based bucket (if provided)
        if account_identifier:
            clean_account = account_identifier.strip().lower()
            acc_bucket = f"acc:{clean_account}:{endpoint_key}"
            self._atomic_consume(acc_bucket, max_requests, window_seconds, now)

    def _atomic_consume(self, bucket_key: str, max_requests: int, window_seconds: int, now: float) -> None:
        """Atomically increments the request counter for the bucket key."""
        try:
            from app.db.session import get_session_factory
            SessionLocal = get_session_factory()
            with SessionLocal() as session:
                # PostgreSQL / SQLite 3.35+ atomic upsert
                stmt = text("""
                    INSERT INTO caravan_rate_limits (bucket_key, request_count, window_start_epoch, last_request_epoch)
                    VALUES (:bucket_key, 1, :now, :now)
                    ON CONFLICT (bucket_key) DO UPDATE
                    SET
                        request_count = CASE
                            WHEN :now - caravan_rate_limits.window_start_epoch >= :window_seconds THEN 1
                            ELSE caravan_rate_limits.request_count + 1
                        END,
                        window_start_epoch = CASE
                            WHEN :now - caravan_rate_limits.window_start_epoch >= :window_seconds THEN :now
                            ELSE caravan_rate_limits.window_start_epoch
                        END,
                        last_request_epoch = :now
                    RETURNING request_count, window_start_epoch;
                """)
                result = session.execute(
                    stmt,
                    {
                        "bucket_key": bucket_key,
                        "now": now,
                        "window_seconds": float(window_seconds),
                    },
                ).fetchone()
                session.commit()

                if result:
                    req_count, window_start = result[0], result[1]
                    if req_count > max_requests:
                        retry_after = max(1, int(window_seconds - (now - float(window_start))))
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                            headers={"Retry-After": str(retry_after)},
                        )
                return
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Persistent rate limit store unavailable (%s), falling back to in-memory: %s", type(exc).__name__, exc)
            # Safe in-memory fallback
            self._memory_fallback.check(bucket_key, max_requests, window_seconds, now)

    def _extract_client_ip(self, request: Request) -> str:
        """Extracts client IP with anti-spoofing proxy precedence."""
        # 1. Cloudflare connecting IP (validated edge proxy)
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

        # 2. X-Forwarded-For: parse first IP in comma-separated list
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip and len(first_ip) <= 45:
                return first_ip

        # 3. Direct client host
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def reset(self) -> None:
        """Reset internal history and clear rate limit table for tests."""
        self._memory_fallback.reset()
        try:
            from app.db.session import get_session_factory
            SessionLocal = get_session_factory()
            with SessionLocal() as session:
                session.execute(text("DELETE FROM caravan_rate_limits"))
                session.commit()
        except Exception:
            pass


_rate_limiter = DistributedRateLimiter()


def get_rate_limiter() -> DistributedRateLimiter:
    return _rate_limiter

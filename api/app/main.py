"""CARAVAN Standalone Platform — Master FastAPI Application Entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import run_migrations, get_session_factory
from app.seed_data import seed_caravan_opportunities
from app.routers import (
    auth,
    opportunities,
    eligibility,
    applications,
    saved,
    account,
    subscriptions,
    support,
    bridge,
    health,
    admin,
    notifications,
    copilot,
    cron,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("caravan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing CARAVAN Standalone Platform...")
    try:
        run_migrations()
    except Exception as mig_err:
        logger.warning("Startup migration non-fatal notice: %s", mig_err)

    try:
        session_factory = get_session_factory()
        with session_factory() as db:
            seeded = seed_caravan_opportunities(db)
            if seeded > 0:
                logger.info("Seeded %d verified institutional funding opportunities.", seeded)
    except Exception as seed_err:
        logger.warning("Startup opportunity seeding non-fatal notice: %s", seed_err)
    yield
    logger.info("CARAVAN Standalone Platform shutting down.")


settings = get_settings()

app = FastAPI(
    title=settings.CARAVAN_APP_NAME,
    description="Institutional Funding Intelligence, Opportunity Matching & Application Operations Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware with strict origin allowlist (disallowing localhost in production)
effective_origins = [
    o for o in settings.CARAVAN_CORS_ORIGINS
    if not (settings.CARAVAN_ENV == "production" and ("localhost" in o or "127.0.0.1" in o))
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=effective_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Enforces standard defensive HTTP security headers on all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(self)"
    if "Strict-Transport-Security" not in response.headers:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' https://challenges.cloudflare.com https://generativelanguage.googleapis.com https://*.supabase.co https://*.vercel.app; "
        "frame-src https://challenges.cloudflare.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

# Include Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(opportunities.router)
app.include_router(eligibility.router)
app.include_router(applications.router)
app.include_router(saved.router)
app.include_router(account.router)
app.include_router(subscriptions.router)
app.include_router(support.router)
app.include_router(bridge.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(copilot.router)
app.include_router(cron.router)

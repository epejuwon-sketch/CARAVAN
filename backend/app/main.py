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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits Vercel previews & custom domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

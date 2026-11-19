"""
Studable API — FastAPI application entry point.

Responsibilities:
- Create and configure the FastAPI app instance.
- Register CORS middleware.
- Mount all API routers under versioned prefixes.
- Expose root and documentation endpoints.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**Studable API** — Social Connection & Networking Platform backend.\n\n"
        "Connect. Discover. Grow."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Origins are loaded from environment variables — never hardcoded here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")


# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"], summary="API root")
def root() -> dict:
    """Returns a friendly message confirming the API is running."""
    return {
        "message": "Studable API is running",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }

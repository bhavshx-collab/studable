"""
Studable API — FastAPI application entry point.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.redis import close_redis_pool
from app.api.routes import health
from app.api.routes import auth as auth_router
from app.api.routes import presence as presence_router
from app.api.websockets import presence_ws

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

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

# ── Lifespan events ───────────────────────────────────────────────────────────


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Gracefully close long-lived connections on shutdown."""
    await close_redis_pool()
    logger.info("Studable API shutdown complete.")


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(OperationalError)
async def db_operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database connection error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service is temporarily unavailable. Please verify database connection."},
    )


# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(presence_router.router, prefix="/api/v1")

# ── WebSocket ─────────────────────────────────────────────────────────────────
app.include_router(presence_ws.router, prefix="/api/v1")


# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"], summary="API root")
def root() -> dict:
    return {
        "message": "Studable API is running",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }

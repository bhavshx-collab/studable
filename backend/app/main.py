"""
Studable API â€” FastAPI application entry point.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.redis import close_redis_pool, get_redis_client
from app.api.routes import health
from app.api.routes import auth as auth_router
from app.api.routes import presence as presence_router
from app.api.routes import ws_ticket
from app.api.routes import matching as matching_router
from app.api.routes import messaging as messaging_router
from app.api.routes import blocks as blocks_router
from app.api.routes import reports as reports_router
from app.api.routes import admin as admin_router
from app.api.routes import user_settings as user_settings_router
from app.api.websockets import presence_ws
from app.api.websockets import matching_ws
from app.api.websockets import messaging_ws
from app.workers.matching_worker import matching_worker_loop

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s â€” %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**Studable API** â€” Social Connection & Networking Platform backend.\n\n"
        "Connect. Discover. Grow."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Background matching worker task handle
_worker_task: Optional[asyncio.Task] = None


# â”€â”€ Lifespan events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize background services (matching engine worker)."""
    global _worker_task
    try:
        redis = get_redis_client()
        _worker_task = asyncio.create_task(matching_worker_loop(redis, interval=2.0))
        logger.info("Matching background worker task created.")
    except Exception as exc:
        logger.warning("Could not start matching background worker: %s", exc)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Gracefully close long-lived connections and background tasks on shutdown."""
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    await close_redis_pool()
    logger.info("Studable API shutdown complete.")


# â”€â”€ Exception handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.exception_handler(OperationalError)
async def db_operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database connection error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service is temporarily unavailable. Please verify database connection."},
    )


# â”€â”€ CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# â”€â”€ Routers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(presence_router.router, prefix="/api/v1")
app.include_router(ws_ticket.router, prefix="/api/v1")
app.include_router(matching_router.router, prefix="/api/v1")
app.include_router(messaging_router.router, prefix="/api/v1")
app.include_router(blocks_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
app.include_router(admin_router.router, prefix="/api/v1")
app.include_router(user_settings_router.router, prefix="/api/v1")

# â”€â”€ WebSockets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.include_router(presence_ws.router, prefix="/api/v1")
app.include_router(matching_ws.router, prefix="/api/v1")
app.include_router(messaging_ws.router, prefix="/api/v1")


# â”€â”€ Root â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/", tags=["Root"], summary="API root")
def root() -> dict:
    return {
        "message": "Studable API is running",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


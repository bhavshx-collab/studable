"""
Studable API — Health check routes.

GET /api/v1/health  — application + database + Redis health
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.database import check_db_connection
from app.core.redis import check_redis_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description=(
        "Returns the operational status of the Studable API, its PostgreSQL "
        "database connection, and its Redis connection. The application is "
        "considered healthy even when external services are temporarily unavailable."
    ),
    response_description="Health status object",
)
async def health_check() -> dict:
    """
    Returns application health and connectivity status for all services.

    - **status**: always `healthy` while the application is running.
    - **service**: service name identifier.
    - **database**: `connected` or `unavailable`.
    - **redis**: `connected` or `unavailable`.
    """
    db_ok = check_db_connection()
    redis_ok = await check_redis_connection()

    return {
        "status": "healthy",
        "service": "Studable API",
        "database": "connected" if db_ok else "unavailable",
        "redis": "connected" if redis_ok else "unavailable",
    }

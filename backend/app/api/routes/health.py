"""
Studable API — Health check routes.

GET /api/v1/health  — application + database health
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description=(
        "Returns the operational status of the Studable API and its "
        "PostgreSQL database connection. The application is considered "
        "healthy even when the database is temporarily unavailable."
    ),
    response_description="Health status object",
)
def health_check() -> dict:
    """
    Returns application health and database connectivity status.

    - **status**: always `healthy` while the application is running.
    - **service**: service name identifier.
    - **database**: `connected` or `unavailable`.
    """
    db_ok = check_db_connection()

    return {
        "status": "healthy",
        "service": "Studable API",
        "database": "connected" if db_ok else "unavailable",
    }

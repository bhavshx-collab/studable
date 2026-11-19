"""
Studable API — Database engine, session factory and base model.

Uses SQLAlchemy 2.0 (sync) with psycopg3.
All models must inherit from Base so Alembic can discover them.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Engine ───────────────────────────────────────────────────────────────────
# pool_pre_ping: drops stale connections automatically before each checkout.
# pool_size / max_overflow: sensible defaults; tune per deployment.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,  # SQL logging only in DEBUG mode
)

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Dependency injection ─────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that yields a database session and ensures it is
    closed when the request finishes (or raises).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Connectivity check ───────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """
    Returns True if a live connection to PostgreSQL can be established,
    False otherwise.  Never raises; logs the error instead.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as exc:
        logger.warning("Database connection failed (OperationalError): %s", exc)
        return False
    except SQLAlchemyError as exc:
        logger.warning("Database connection failed (SQLAlchemyError): %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database connection failed (unexpected): %s", exc)
        return False

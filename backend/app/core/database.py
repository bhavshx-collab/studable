"""
Studable API — Database engine, session factory and declarative base.

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


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
)

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Dependency injection ─────────────────────────────────────────────────────
def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Connectivity check ───────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """Returns True if PostgreSQL is reachable. Never raises."""
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

"""
Studable API — Database engine, session factory and declarative base.

Uses SQLAlchemy 2.0 (sync) with psycopg3 for PostgreSQL.
In development mode, if PostgreSQL is not running on localhost,
it falls back to a local SQLite database (studable_dev.db) so that
the frontend and backend remain fully functional for local testing.
"""

from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Engine initialization ─────────────────────────────────────────────────────

_is_fallback_sqlite: bool = False


def _create_sqlite_engine(url: str):
    """Create a SQLite engine configured with foreign key enforcement."""
    eng = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG,
    )

    @event.listens_for(eng, "connect")
    def _enable_fk(dbapi_connection, connection_record):  # pylint: disable=unused-argument
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


def _init_engine():
    global _is_fallback_sqlite

    # If explicitly configured for SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        logger.info("Using SQLite database: %s", settings.DATABASE_URL)
        eng = _create_sqlite_engine(settings.DATABASE_URL)
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=eng)
        _is_fallback_sqlite = True
        return eng

    # Attempt PostgreSQL connection
    pg_engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.DEBUG,
        connect_args={"connect_timeout": 2},
    )

    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to primary PostgreSQL database at %s", settings.DATABASE_URL)
        _is_fallback_sqlite = False
        return pg_engine
    except Exception as exc:  # pylint: disable=broad-except
        if settings.ENVIRONMENT == "development":
            logger.warning(
                "PostgreSQL is unreachable at %s (%s). "
                "Activating local SQLite fallback (studable_dev.db) for development.",
                settings.DATABASE_URL,
                exc,
            )
            eng = _create_sqlite_engine("sqlite:///./studable_dev.db")
            import app.models  # noqa: F401
            Base.metadata.create_all(bind=eng)
            _is_fallback_sqlite = True
            logger.info("SQLite dev database ready (studable_dev.db).")
            return eng

        # In production/staging, do not silently fallback
        logger.error("Database connection failed in %s mode: %s", settings.ENVIRONMENT, exc)
        _is_fallback_sqlite = False
        return pg_engine


engine = _init_engine()


# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Dependency injection ─────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Connectivity check ───────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """Returns True if the active database is reachable. Never raises."""
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


def is_using_sqlite_fallback() -> bool:
    """Return whether the current engine is using the dev SQLite fallback."""
    return _is_fallback_sqlite

"""
Alembic environment configuration — Studable API.

Loads the DATABASE_URL from environment variables (via app.core.config)
and registers all SQLAlchemy models so Alembic can generate accurate
auto-migrations in future phases.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make the app package importable ──────────────────────────────────────────
# Alembic runs from the backend/ directory; add it to sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Import Base and all models so Alembic can see them ───────────────────────
from app.core.database import Base  # noqa: E402
from app.core.config import settings  # noqa: E402

# Import model modules here as they are created so their tables are registered:
# from app.models import user  # example — uncomment when model exists

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url with the value from our Settings object.
# This means the database URL is always read from the environment / .env file.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support.
target_metadata = Base.metadata


# ── Migration helpers ─────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

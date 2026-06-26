"""Alembic environment. We run migrations against DATABASE_URL using raw SQL (no ORM
models), so there's no `target_metadata` — each migration spells out its own DDL.
"""
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# Read the URL from the environment (same DATABASE_URL the app uses). SQLAlchemy needs
# the driver named explicitly to use psycopg 3, so rewrite postgresql:// -> +psycopg.
url = os.environ.get("DATABASE_URL", "")
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
config.set_main_option("sqlalchemy.url", url)


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()

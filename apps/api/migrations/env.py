"""Alembic environment.

Migrations run synchronously (psycopg) even though the application is async -
there is no reason for a migration to be concurrent, and the sync driver has
far better error messages when DDL fails.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from justnews_core.models import Base
from justnews_core.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# set_main_option writes through configparser's interpolation, which treats a
# bare "%" as the start of a "%(name)s" reference - and a URL-encoded special
# character in the password (e.g. "%40" for "@") is exactly that. Escaping to
# "%%" here is configparser's own documented workaround, not a URL-encoding
# concern; the escaped value is unescaped again on the way back out.
config.set_main_option("sqlalchemy.url", settings.sync_database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

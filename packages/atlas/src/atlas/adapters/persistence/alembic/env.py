"""Alembic environment configuration."""

import os
from logging.config import fileConfig

from alembic import context
from atlas.adapters.persistence.tables import Base
from atlas.platform.config import get_settings
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get database sync url from settings or environment."""
    # Tests inject sqlalchemy.url into the alembic config object directly
    url_from_config = config.get_main_option("sqlalchemy.url")
    if url_from_config:
        return url_from_config

    settings = get_settings()
    env_url = os.getenv("ATLAS_DATABASE_SYNC_URL", settings.database_sync_url)
    return env_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

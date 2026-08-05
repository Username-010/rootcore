"""Alembic migration environment (async SQLAlchemy)."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base
from app.modules.identity.models import RefreshToken, User  # noqa: F401
from app.modules.households.models import Household, Invitation, Membership  # noqa: F401
from app.modules.taxonomy.models import CareProfile, Taxon  # noqa: F401
from app.modules.plants.models import Plant, PlantPhoto, PlantTag, Tag  # noqa: F401
from app.modules.tasks.models import Task, TaskPlant  # noqa: F401
from app.modules.timeline.models import Event  # noqa: F401
from app.modules.watering.models import WateringState  # noqa: F401
from app.modules.layout.models import Container, Placement, Site, Space  # noqa: F401
from app.modules.weather.models import WeatherCache  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

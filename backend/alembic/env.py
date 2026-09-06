"""Alembic 异步迁移入口。"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.database import Base
from app.models import (  # noqa: F401
    favorite,
    freight,
    idempotency,
    inventory,
    notification,
    operation_log,
    order,
    page,
    product,
    refund,
    review,
    system_setting,
    user,
)

config = context.config
if config.config_file_name is not None and config.file_config.has_section("formatters"):
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """生成离线迁移 SQL。"""
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """创建异步连接并运行在线迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    async def run() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(_configure_and_migrate)
        await connectable.dispose()

    def _configure_and_migrate(sync_connection: Connection) -> None:
        context.configure(connection=sync_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(run())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

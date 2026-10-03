import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from chat_service.app.core.database import Base
from chat_service.app.models import Chat, ChatUser, Message  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


async def run_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn, target_metadata=target_metadata
            )
        )
        await connection.begin()
        await connection.run_sync(lambda _: context.run_migrations())
        await connection.commit()

    await connectable.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline mode is not supported for async migrations")
else:
    asyncio.run(run_migrations())

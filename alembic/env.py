import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from src.base.model import Base
from src.core.config import settings
from src.modules.auth.models import Auth  # noqa: F401
from src.modules.behavior.models import BehaviorAccountState, BehaviorChatState  # noqa: F401
from src.modules.memory.models import (  # noqa: F401
    Conversation,
    Message,
    MessageBatch,
    SummaryState,
    VectorRecord,
)
from src.modules.telegram_clients.models import (  # noqa: F401
    TelegramAccount,
    TelegramChatState,
    TelegramSettings,
)
from src.modules.users.models import User  # noqa: F401
from src.modules.instagram_clients.models import (  # noqa: F401
    InstagramAccount,
    InstagramChatState,
    InstagramSettings,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return settings.DATABASE_URL


config.set_main_option("sqlalchemy.url", get_url().replace("%", "%%"))


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

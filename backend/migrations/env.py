import asyncio
import threading
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from src.core.settings import settings
from src.models.user import table_registry
from src.models.llm_model import LLMModel as _LLMModel  # noqa: F401 — registers table in metadata


config = context.config

# Override the URL from settings — this respects DATABASE_URL and individual
# POSTGRES_* vars. Uses the asyncpg driver (postgresql+asyncpg://).
config.set_main_option("sqlalchemy.url", settings.db_url)

# Only reconfigure logging when running from CLI (main thread).
# When invoked programmatically via asyncio.to_thread(), fileConfig()
# causes a cross-thread deadlock with the application's logging.
# See: https://github.com/sqlalchemy/alembic/discussions/1483
if config.config_file_name is not None and threading.current_thread() is threading.main_thread():
    fileConfig(config.config_file_name)

target_metadata = table_registry.metadata

# Track this project's migrations in a dedicated version table. Aegra runs its
# own bundled migration chain against the SAME database using the default
# "alembic_version" table; if we shared it, whichever chain ran second would
# read the other's revision id and abort with "Can't locate revision". A
# separate table keeps the two independent chains from colliding.
VERSION_TABLE = "alembic_version_app"

# Only manage tables that are explicitly defined in our models.
# This prevents autogenerate from generating DROP TABLE statements for
# tables owned by Aegra (checkpoints, runs, threads, etc.).
_our_tables = set(target_metadata.tables.keys())


def include_object(
    object: object, name: str, type_: str, reflected: bool, compare_to: object
) -> bool:
    if type_ == "table":
        return name in _our_tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection needed)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table=VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table=VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect with async engine (asyncpg) and run migrations via run_sync."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    asyncio.run() is safe here because Aegra calls this function from
    asyncio.to_thread(), which runs it in a plain thread with no active
    event loop.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

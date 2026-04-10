import asyncio
import threading
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from src.core.settings import settings
from src.models.user import table_registry


def _ensure_aegra_tables() -> None:
    """Create Aegra's internal tables if they do not exist.

    Aegra's migration resolver picks up the project's alembic.ini first,
    so its own migration scripts (assistant, runs, threads, etc.) are never
    applied on a fresh database. Using create_all(checkfirst=True) ensures
    those tables are present before the project's migrations run, without
    interfering with Alembic's version tracking.

    Limitation: this handles missing *tables* (fresh DB). If a future Aegra
    upgrade adds *columns* to existing tables, a `docker compose down -v` is
    needed in development (or a manual ALTER TABLE in production) until Aegra
    fixes the upstream bug in its migration resolver.
    """
    try:
        from aegra_api.core.orm import Base as _AegraBase
        from aegra_api.settings import settings as _aegra_settings
    except ImportError:
        return

    from sqlalchemy.ext.asyncio import create_async_engine

    async def _create() -> None:
        _engine = create_async_engine(_aegra_settings.db.database_url)
        try:
            async with _engine.begin() as _conn:
                await _conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                await _conn.run_sync(_AegraBase.metadata.create_all, checkfirst=True)
        finally:
            await _engine.dispose()

    asyncio.run(_create())


_ensure_aegra_tables()

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
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
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

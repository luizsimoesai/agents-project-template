from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.settings import settings

# create_async_engine is the async equivalent of create_engine.
# It uses asyncpg under the hood, which is a non-blocking PostgreSQL driver
# that works natively with Python's asyncio (and therefore with FastAPI).
engine = create_async_engine(
    settings.db_url,
    echo=settings.db_echo_log,  # print SQL statements when True
    pool_size=settings.sqlalchemy_pool_size,
    max_overflow=settings.sqlalchemy_max_overflow,
)

# async_sessionmaker creates AsyncSession instances.
# expire_on_commit=False → after committing, objects stay accessible without
# triggering new DB queries. This is important in async code because a lazy
# load after the session closes would raise an error.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

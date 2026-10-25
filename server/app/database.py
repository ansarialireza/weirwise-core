from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from server.app.config import get_settings

settings = get_settings()

# Engine creation:
# Note: For SQLite testing or PostgreSQL, handle connection arguments appropriately.
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.database_url,
    echo=(settings.log_level.upper() == "DEBUG"),
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from datetime import datetime, timezone
from src.db.models import Base, DocumentRecord
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)



def get_engine():
    """Create async SQLAlchemy engine using settings from config.
    
    Uses asyncpg driver for non-blocking database operations.
    Connection String format: postgreSQL+asyncpg://user:password@host:port/db
    """

    settings = get_settings()
    connection_string=(
        f"postgresql+asyncpg://{settings.postgres_username}:"
        f"{settings.postgres_password}@{settings.postgres_host}:"
        f"{settings.postgres_port}/{settings.postgres_db}"
    )
    return create_async_engine(connection_string, echo=settings.debug)


def get_session_factory():
    """Create async session factory bound to the engine."""
    engine = get_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Create all tables if they dont exist yet.
    
    Called once at Application startup via the lifespan function in main.py.
    Safe to call multiple times, only creates tables that do not exist. 
    """
    engine=get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_initialised")


async def get_db():
    """FastAPI dependency that provides a database session per request.
    
    Yields a session and closes it automatically when the request ends.
    Use with Depends(get_db) in endpoint functions.
    """
    session_factory=get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

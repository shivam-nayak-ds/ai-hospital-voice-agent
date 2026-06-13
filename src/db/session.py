import urllib.parse
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
from config.settings import settings
from src.utils.logger import custom_logger as logger

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Build dynamic PostgreSQL URL if not already defined (ensures settings is loaded)
db_url = settings.DATABASE_URL
if not db_url:
    quoted_password = urllib.parse.quote_plus(settings.DB_PASSWORD) if settings.DB_PASSWORD else ""
    password_part = f":{quoted_password}" if quoted_password else ""
    db_url = f"postgresql+psycopg://{settings.DB_USER}{password_part}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

logger.info(f"Initializing Async PostgreSQL engine with connection pooling (Pool Size: {settings.DB_POOL_SIZE})")

try:
    # ─── Connection Pooling Strategy ──────────────────────────────────────────
    # pool_pre_ping=True: Automatically checks if a connection is alive before using it
    # pool_recycle=1800: Recycle connections after 30 minutes to prevent memory leaks/timeouts
    # max_overflow=10: Allow up to 10 additional connections beyond the pool size during peak loads
    engine = create_async_engine(
        db_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": settings.DB_CONNECTION_TIMEOUT}
    )
    logger.success("Async PostgreSQL engine created successfully.")
except Exception as e:
    logger.error(f"Failed to create Async PostgreSQL engine: {e}")
    raise e

AsyncSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=engine
)
Base = declarative_base()

@asynccontextmanager
async def get_db():
    """
    Async context manager for database sessions.
    Ensures rollback on exceptions and automatic clean pool release.
    """
    db = AsyncSessionLocal()
    try:
        yield db
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Database transaction rolled back due to error: {e}")
        raise e
    finally:
        await db.close()

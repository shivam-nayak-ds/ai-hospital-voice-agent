import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager
from config.settings import settings
from src.utils.logger import custom_logger as logger

# Build dynamic PostgreSQL URL if not already defined (ensures settings is loaded)
db_url = settings.DATABASE_URL
if not db_url:
    quoted_password = urllib.parse.quote_plus(settings.DB_PASSWORD) if settings.DB_PASSWORD else ""
    password_part = f":{quoted_password}" if quoted_password else ""
    db_url = f"postgresql+psycopg://{settings.DB_USER}{password_part}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

logger.info(f"Initializing PostgreSQL engine with connection pooling (Pool Size: {settings.DB_POOL_SIZE})")

try:
    # ─── Connection Pooling Strategy ──────────────────────────────────────────
    # pool_pre_ping=True: Automatically checks if a connection is alive before using it
    # pool_recycle=1800: Recycle connections after 30 minutes to prevent memory leaks/timeouts
    # max_overflow=10: Allow up to 10 additional connections beyond the pool size during peak loads
    engine = create_engine(
        db_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": settings.DB_CONNECTION_TIMEOUT}
    )
    logger.success("PostgreSQL engine created successfully.")
except Exception as e:
    logger.error(f"Failed to create PostgreSQL engine: {e}")
    raise e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db():
    """
    Context manager for database sessions.
    Ensures rollback on exceptions and automatic clean pool release.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction rolled back due to error: {e}")
        raise e
    finally:
        db.close()

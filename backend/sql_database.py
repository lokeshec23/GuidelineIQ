# backend/sql_database.py
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import SQL_SERVER_URI

from sqlalchemy import text
from config import SQL_SERVER_URI, DB_NAME

# Configure logging
logger = logging.getLogger(__name__)

def get_master_uri(uri: str, db_name: str) -> str:
    """Derives the master database URI from the main URI."""
    if f"/{db_name}" in uri:
        return uri.replace(f"/{db_name}", "/master")
    return uri # Fallback

# Create Async Engine
# echo=True will log SQL queries (useful for debugging)
engine = create_async_engine(SQL_SERVER_URI, echo=False)

# Create Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

async def get_db():
    """
    Dependency to get a database session.
    Yields an AsyncSession.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize database tables.
    Should be called on application startup.
    """
    # First, ensure the database exists
    master_uri = get_master_uri(SQL_SERVER_URI, DB_NAME)
    master_engine = create_async_engine(master_uri, isolation_level="AUTOCOMMIT")
    
    try:
        async with master_engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(text(f"SELECT name FROM sys.databases WHERE name = '{DB_NAME}'"))
            if not result.fetchone():
                logger.info(f"Database '{DB_NAME}' does not exist. Creating...")
                await conn.execute(text(f"CREATE DATABASE [{DB_NAME}]"))
                logger.info(f"✅ Database '{DB_NAME}' created successfully.")
            else:
                logger.info(f"Database '{DB_NAME}' already exists.")
    except Exception as e:
        logger.error(f"⚠️ Error checking/creating database: {e}")
        # We continue anyway, as the main engine might still work if it was a false alarm
        # or it will fail with a clearer error.
    finally:
        await master_engine.dispose()

    # Now initialize tables
    try:
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all) # Uncomment to reset DB
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ SQL Server tables initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize SQL Server tables: {e}")
        raise e

async def close_db():
    """
    Close database connection.
    """
    await engine.dispose()
    logger.info("SQL Server connection closed.")

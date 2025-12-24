# backend/database.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from config import MONGO_URI, DB_NAME

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Singleton class to manage MongoDB connection.
    Follows the Singleton pattern to ensure only one database connection exists.
    """
    _instance = None
    client: AsyncIOMotorClient = None
    db = None
    fs = None
    
    # Collections
    users = None
    settings = None
    ingest_history = None
    compare_history = None
    user_prompts = None
    default_prompts = None
    gemini_file_cache = None
    chat_sessions = None
    chat_conversations = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        """Initialize MongoDB connection."""
        if self.client:
            return  # Already connected

        try:
            logger.info("Connecting to MongoDB...")
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            
            # Initialize Collections
            self.users = self.db["users"]
            self.settings = self.db["settings"]
            self.ingest_history = self.db["ingest_history"]
            self.compare_history = self.db["compare_history"]
            self.user_prompts = self.db["user_prompts"]
            self.default_prompts = self.db["default_prompts"]
            self.gemini_file_cache = self.db["gemini_file_cache"]
            self.chat_sessions = self.db["chat_sessions"]
            self.chat_conversations = self.db["chat_conversations"]
            
            # Initialize GridFS
            self.fs = AsyncIOMotorGridFSBucket(self.db)
            
            logger.info("✅ MongoDB connection successful.")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise e

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("MongoDB connection closed.")

# Global instance
db_manager = DatabaseManager()

async def get_database():
    """Dependency to get the database instance."""
    if not db_manager.client:
        await db_manager.connect()
    return db_manager.db

# Collection getters for backward compatibility / direct access if strictly needed
# Ideally, services should use the db_manager instance or the get_database dependency
def get_collection(collection_name: str):
    if not db_manager.db:
         raise RuntimeError("Database not initialized")
    return db_manager.db[collection_name]

# backend/database.py

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from config import MONGO_URI, DB_NAME

# Initialize MongoDB client and database
client = None
db = None
users_collection = None
settings_collection = None
ingest_history_collection = None
compare_history_collection = None
user_prompts_collection = None
default_prompts_collection = None
gemini_file_cache_collection = None
chat_sessions_collection = None
chat_conversations_collection = None

# GridFS for PDF storage
fs = None

def get_database():
    """Get or create database connection."""
    global client, db, users_collection, settings_collection
    global ingest_history_collection, compare_history_collection
    global user_prompts_collection, default_prompts_collection
    global gemini_file_cache_collection
    global chat_sessions_collection, chat_conversations_collection, fs
    
    if client is None:
        try:
            client = AsyncIOMotorClient(MONGO_URI)
            db = client[DB_NAME]
            users_collection = db["users"]
            settings_collection = db["settings"]
            ingest_history_collection = db["ingest_history"]
            compare_history_collection = db["compare_history"]
            user_prompts_collection = db["user_prompts"]
            default_prompts_collection = db["default_prompts"]
            gemini_file_cache_collection = db["gemini_file_cache"]
            chat_sessions_collection = db["chat_sessions"]
            chat_conversations_collection = db["chat_conversations"]
            
            # Initialize GridFS bucket for PDF storage
            fs = AsyncIOMotorGridFSBucket(db)
            
            print("✅ MongoDB connection successful.")
            print("✅ GridFS bucket initialized.")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
    
    return db

# Initialize on import - REMOVED to prevent event loop mismatch
# The database will be initialized by the startup event in main.py

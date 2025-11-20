# backend/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

# Initialize MongoDB client and database
client = None
db = None
users_collection = None
settings_collection = None
ingest_history_collection = None
compare_history_collection = None

try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db["users"]
    settings_collection = db["settings"]
    ingest_history_collection = db["ingest_history"]
    compare_history_collection = db["compare_history"]
    print("✅ MongoDB connection successful.")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

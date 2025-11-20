# backend/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

# Initialize MongoDB client and database
client = None
db = None
users_collection = None
settings_collection = None

try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db["users"]
    settings_collection = db["settings"]
    print("✅ MongoDB connection successful.")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

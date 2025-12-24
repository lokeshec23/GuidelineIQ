# backend/auth/models.py
from bson import ObjectId
from database import db_manager

async def find_user_by_email(email: str):
    """Find a user by email address."""
    if db_manager.users is None:
        # Try to connect if not initialized (though lifespan should have handled this)
        await db_manager.connect()
        
    return await db_manager.users.find_one({"email": email})

async def get_user_by_id(user_id: str):
    """Find a user by their ID."""
    if db_manager.users is None:
        await db_manager.connect()
        
    return await db_manager.users.find_one({"_id": ObjectId(user_id)})

async def create_user(user_data: dict):
    """Create a new user."""
    if db_manager.users is None:
        await db_manager.connect()
        
    result = await db_manager.users.insert_one(user_data)
    return await db_manager.users.find_one({"_id": result.inserted_id})
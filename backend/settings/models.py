# backend/settings/models.py

import database
from typing import Optional, Dict

async def get_user_settings(user_id: str) -> Optional[Dict]:
    """Fetch settings for a specific user"""
    if database.settings_collection is None:
        return None
    return await database.settings_collection.find_one({"user_id": user_id})

async def create_or_update_settings(user_id: str, settings: dict):
    """Update or create settings for a user"""
    if database.settings_collection is None:
        raise ConnectionError("Database not initialized")
        
    await database.settings_collection.update_one(
        {"user_id": user_id},
        {"$set": settings},
        upsert=True
    )
    return await get_user_settings(user_id)

async def delete_user_settings(user_id: str):
    """Delete settings for a user"""
    if database.settings_collection is None:
        raise ConnectionError("Database not initialized")
        
    return await database.settings_collection.delete_one({"user_id": user_id})
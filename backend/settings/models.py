# backend/settings/models.py

from database import db_manager
from typing import Optional, Dict
from datetime import datetime

async def _ensure_db():
    if not db_manager.client:
        await db_manager.connect()

async def get_user_settings(user_id: str) -> Optional[Dict]:
    """Fetch settings for a specific user"""
    await _ensure_db()
    if db_manager.settings is None:
        return None
    return await db_manager.settings.find_one({"user_id": user_id})

async def create_or_update_settings(user_id: str, settings: dict):
    """Update or create settings for a user"""
    await _ensure_db()
    
    # Always add the updated_at timestamp
    settings["updated_at"] = datetime.utcnow()
        
    await db_manager.settings.update_one(
        {"user_id": user_id},
        {"$set": settings},
        upsert=True
    )
    return await get_user_settings(user_id)

async def delete_user_settings(user_id: str):
    """Delete settings for a user"""
    await _ensure_db()
        
    return await db_manager.settings.delete_one({"user_id": user_id})
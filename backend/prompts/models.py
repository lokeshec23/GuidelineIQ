# backend/prompts/models.py

import database
from typing import Optional, Dict

async def get_user_prompts(user_id: str) -> Optional[Dict]:
    """Fetch custom prompts for a specific user"""
    if database.user_prompts_collection is None:
        return None
    return await database.user_prompts_collection.find_one({"user_id": user_id})

async def save_user_prompts(user_id: str, prompts_data: dict):
    """Update or create custom prompts for a user"""
    if database.user_prompts_collection is None:
        raise ConnectionError("Database not initialized")
        
    await database.user_prompts_collection.update_one(
        {"user_id": user_id},
        {"$set": prompts_data},
        upsert=True
    )
    return await get_user_prompts(user_id)

async def reset_user_prompts(user_id: str):
    """Delete custom prompts for a user (revert to defaults)"""
    if database.user_prompts_collection is None:
        raise ConnectionError("Database not initialized")
        
    return await database.user_prompts_collection.delete_one({"user_id": user_id})

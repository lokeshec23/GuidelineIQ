# backend/prompts/models.py

from datetime import datetime
from typing import Dict, Optional
from database import user_prompts_collection
from bson import ObjectId


async def get_user_prompts(user_id: str) -> Optional[Dict]:
    """
    Get user's prompts. If not exists, create with defaults from config.
    """
    user_prompts = await user_prompts_collection.find_one({"user_id": ObjectId(user_id)})
    
    if user_prompts:
        # Convert ObjectId to string for JSON serialization
        user_prompts["_id"] = str(user_prompts["_id"])
        user_prompts["user_id"] = str(user_prompts["user_id"])
        return user_prompts
    
    # Create default prompts for new user
    from config import (
        DEFAULT_INGEST_PROMPT_SYSTEM,
        DEFAULT_INGEST_PROMPT_USER,
        DEFAULT_COMPARISON_PROMPT_SYSTEM,
        DEFAULT_COMPARISON_PROMPT_USER
    )
    
    default_prompts = {
        "user_id": ObjectId(user_id),
        "ingest_prompts": {
            "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM,
            "user_prompt": DEFAULT_INGEST_PROMPT_USER
        },
        "compare_prompts": {
            "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM,
            "user_prompt": DEFAULT_COMPARISON_PROMPT_USER
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await user_prompts_collection.insert_one(default_prompts)
    default_prompts["_id"] = str(result.inserted_id)
    default_prompts["user_id"] = str(user_id)
    
    return default_prompts


async def save_user_prompts(user_id: str, prompts: Dict) -> bool:
    """
    Save/update user's custom prompts.
    """
    update_data = {
        "ingest_prompts": prompts.get("ingest_prompts", {}),
        "compare_prompts": prompts.get("compare_prompts", {}),
        "updated_at": datetime.utcnow()
    }
    
    result = await user_prompts_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    return result.modified_count > 0


async def reset_user_prompts(user_id: str) -> bool:
    """
    Reset user's prompts to defaults from config.
    """
    from config import (
        DEFAULT_INGEST_PROMPT_SYSTEM,
        DEFAULT_INGEST_PROMPT_USER,
        DEFAULT_COMPARISON_PROMPT_SYSTEM,
        DEFAULT_COMPARISON_PROMPT_USER
    )
    
    reset_data = {
        "ingest_prompts": {
            "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM,
            "user_prompt": DEFAULT_INGEST_PROMPT_USER
        },
        "compare_prompts": {
            "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM,
            "user_prompt": DEFAULT_COMPARISON_PROMPT_USER
        },
        "updated_at": datetime.utcnow()
    }
    
    result = await user_prompts_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": reset_data}
    )
    
    return result.modified_count > 0


async def initialize_user_prompts(user_id: str) -> bool:
    """
    Initialize default prompts for a new user (called on registration).
    """
    # Check if already exists
    existing = await user_prompts_collection.find_one({"user_id": ObjectId(user_id)})
    if existing:
        return True
    
    # Create with defaults
    await get_user_prompts(user_id)
    return True

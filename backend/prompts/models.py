# backend/prompts/models.py

import database
from typing import Optional, Dict
from config import (
    DEFAULT_INGEST_PROMPT_USER_OPENAI,
    DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI,
    DEFAULT_INGEST_PROMPT_USER_GEMINI,
    DEFAULT_INGEST_PROMPT_SYSTEM_GEMINI,
    DEFAULT_COMPARISON_PROMPT_USER_OPENAI,
    DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI,
    DEFAULT_COMPARISON_PROMPT_USER_GEMINI,
    DEFAULT_COMPARISON_PROMPT_SYSTEM_GEMINI,
)

async def get_default_prompts_from_db() -> Optional[Dict]:
    """Fetch default prompts from database"""
    if database.default_prompts_collection is None:
        return None
    
    try:
        default_doc = await database.default_prompts_collection.find_one({"_id": "system_defaults"})
        if default_doc:
            # Remove MongoDB _id field
            default_doc.pop("_id", None)
            return default_doc
    except Exception as e:
        print(f"⚠️ Failed to fetch default prompts from database: {e}")
    
    return None


def get_default_prompts() -> Dict:
    """Return default prompts - from config as fallback"""
    return {
        "ingest_prompts": {
            "openai": {
                "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI,
                "user_prompt": DEFAULT_INGEST_PROMPT_USER_OPENAI,
            },
            "gemini": {
                "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM_GEMINI,
                "user_prompt": DEFAULT_INGEST_PROMPT_USER_GEMINI,
            },
        },
        "compare_prompts": {
            "openai": {
                "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI,
                "user_prompt": DEFAULT_COMPARISON_PROMPT_USER_OPENAI,
            },
            "gemini": {
                "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM_GEMINI,
                "user_prompt": DEFAULT_COMPARISON_PROMPT_USER_GEMINI,
            },
        },
    }

async def get_user_prompts(user_id: str) -> Dict:
    """Fetch custom prompts for a specific user, or return defaults if none exist"""
    if database.user_prompts_collection is None:
        return get_default_prompts()
    
    user_prompts = await database.user_prompts_collection.find_one({"user_id": user_id})
    
    # If no custom prompts exist, return defaults from database (or config fallback)
    if not user_prompts:
        db_defaults = await get_default_prompts_from_db()
        return db_defaults if db_defaults else get_default_prompts()
    
    # Merge user prompts with defaults to ensure all models have prompts
    db_defaults = await get_default_prompts_from_db()
    defaults = db_defaults if db_defaults else get_default_prompts()
    
    # Merge ingest_prompts
    if "ingest_prompts" not in user_prompts:
        user_prompts["ingest_prompts"] = defaults["ingest_prompts"]
    else:
        # Ensure both openai and gemini exist
        if "openai" not in user_prompts["ingest_prompts"]:
            user_prompts["ingest_prompts"]["openai"] = defaults["ingest_prompts"]["openai"]
        if "gemini" not in user_prompts["ingest_prompts"]:
            user_prompts["ingest_prompts"]["gemini"] = defaults["ingest_prompts"]["gemini"]
    
    # Merge compare_prompts
    if "compare_prompts" not in user_prompts:
        user_prompts["compare_prompts"] = defaults["compare_prompts"]
    else:
        # Ensure both openai and gemini exist
        if "openai" not in user_prompts["compare_prompts"]:
            user_prompts["compare_prompts"]["openai"] = defaults["compare_prompts"]["openai"]
        if "gemini" not in user_prompts["compare_prompts"]:
            user_prompts["compare_prompts"]["gemini"] = defaults["compare_prompts"]["gemini"]
    
    return user_prompts

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
    
    await database.user_prompts_collection.delete_one({"user_id": user_id})
    return True

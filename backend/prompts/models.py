# backend/prompts/models.py

from database import db_manager
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

async def _ensure_db():
    if not db_manager.client:
        await db_manager.connect()

async def get_default_prompts_from_db() -> Optional[Dict]:
    """Fetch default prompts from database"""
    await _ensure_db()
    if db_manager.default_prompts is None:
        return None
    
    try:
        default_doc = await db_manager.default_prompts.find_one({"_id": "system_defaults"})
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
    await _ensure_db()
    
    if db_manager.user_prompts is None:
         return get_default_prompts()
    
    user_prompts = await db_manager.user_prompts.find_one({"user_id": user_id})
    
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
    await _ensure_db()
    
    await db_manager.user_prompts.update_one(
        {"user_id": user_id},
        {"$set": prompts_data},
        upsert=True
    )
    return await get_user_prompts(user_id)

async def initialize_user_prompts(user_id: str):
    """Initialize default prompts for a new user"""
    # Simply ensures the prompt document exists but empty or same as default
    # Actually, we might want to COPY defaults to user collection if we want them decoupled later
    # For now, let's just do nothing as get_user_prompts handles fallback.
    pass

async def reset_user_prompts(user_id: str):
    """Delete custom prompts for a user (revert to defaults)"""
    await _ensure_db()
    
    await db_manager.user_prompts.delete_one({"user_id": user_id})
    return True

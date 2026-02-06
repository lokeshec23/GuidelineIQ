# backend/prompts/models.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from models.sql_models import UserPrompts, DefaultPrompts
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

# _ensure_db removed


async def get_default_prompts_from_db(db: AsyncSession) -> Optional[Dict]:
    """Fetch default prompts from database"""
    result = await db.execute(select(DefaultPrompts).where(DefaultPrompts.id == "system_defaults"))
    default_doc = result.scalars().first()
    
    if default_doc:
        return {
            "ingest_prompts": default_doc.ingest_prompts,
            "compare_prompts": default_doc.compare_prompts
        }
    
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

async def get_user_prompts(db: AsyncSession, user_id: str) -> Dict:
    """Fetch custom prompts for a specific user, or return defaults if none exist"""
    result = await db.execute(select(UserPrompts).where(UserPrompts.user_id == user_id))
    user_prompts_obj = result.scalars().first()
    
    # If no custom prompts exist, return defaults from database (or config fallback)
    if not user_prompts_obj:
        db_defaults = await get_default_prompts_from_db(db)
        return db_defaults if db_defaults else get_default_prompts()
    
    user_prompts = {
        "ingest_prompts": user_prompts_obj.ingest_prompts,
        "compare_prompts": user_prompts_obj.compare_prompts
    }
    
    # Merge user prompts with defaults to ensure all models have prompts
    db_defaults = await get_default_prompts_from_db(db)
    defaults = db_defaults if db_defaults else get_default_prompts()
    
    # Merge ingest_prompts
    if "ingest_prompts" not in user_prompts or not user_prompts["ingest_prompts"]:
        user_prompts["ingest_prompts"] = defaults["ingest_prompts"]
    else:
        # Ensure both openai and gemini exist
        if "openai" not in user_prompts["ingest_prompts"]:
            user_prompts["ingest_prompts"]["openai"] = defaults["ingest_prompts"]["openai"]
        if "gemini" not in user_prompts["ingest_prompts"]:
             user_prompts["ingest_prompts"]["gemini"] = defaults["ingest_prompts"]["gemini"]
    
    # Merge compare_prompts
    if "compare_prompts" not in user_prompts or not user_prompts["compare_prompts"]:
        user_prompts["compare_prompts"] = defaults["compare_prompts"]
    else:
        # Ensure both openai and gemini exist
        if "openai" not in user_prompts["compare_prompts"]:
            user_prompts["compare_prompts"]["openai"] = defaults["compare_prompts"]["openai"]
        if "gemini" not in user_prompts["compare_prompts"]:
            user_prompts["compare_prompts"]["gemini"] = defaults["compare_prompts"]["gemini"]
    
    return user_prompts

async def save_user_prompts(db: AsyncSession, user_id: str, prompts_data: dict):
    """Update or create custom prompts for a user"""
    result = await db.execute(select(UserPrompts).where(UserPrompts.user_id == user_id))
    user_prompts_obj = result.scalars().first()
    
    if user_prompts_obj:
        # Update existing
        if "ingest_prompts" in prompts_data:
            user_prompts_obj.ingest_prompts = prompts_data["ingest_prompts"]
        if "compare_prompts" in prompts_data:
            user_prompts_obj.compare_prompts = prompts_data["compare_prompts"]
    else:
        # Create new
        user_prompts_obj = UserPrompts(
            user_id=user_id,
            ingest_prompts=prompts_data.get("ingest_prompts", {}),
            compare_prompts=prompts_data.get("compare_prompts", {})
        )
        db.add(user_prompts_obj)
        
    await db.commit()
    await db.refresh(user_prompts_obj)
    
    return await get_user_prompts(db, user_id)

async def initialize_user_prompts(user_id: str):
    """Initialize default prompts for a new user"""
    # Simply ensures the prompt document exists but empty or same as default
    # For now, let's just do nothing as get_user_prompts handles fallback.
    pass

async def reset_user_prompts(db: AsyncSession, user_id: str):
    """Delete custom prompts for a user (revert to defaults)"""
    stmt = delete(UserPrompts).where(UserPrompts.user_id == user_id)
    await db.execute(stmt)
    await db.commit()
    return True

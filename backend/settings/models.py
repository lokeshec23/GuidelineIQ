# backend/settings/models.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.sql_models import UserSettings
from typing import Optional, Dict
from datetime import datetime

async def get_user_settings(db: AsyncSession, user_id: str) -> Optional[Dict]:
    """Fetch settings for a specific user"""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalars().first()
    
    if not user_settings:
        return None
    
    # Return merged dict: settings_json + metadata
    data = user_settings.settings_json or {}
    
    # --- Migration guard: auto-fix stale Gemini provider settings ---
    # if data.get("default_model_provider") == "gemini":
    #     data["default_model_provider"] = "openai"
    #     data["default_model_name"] = "gpt-4o"
    #     # Remove stale gemini_api_key if present
    #     data.pop("gemini_api_key", None)
    #     # Persist the fix
    #     user_settings.settings_json = data
    #     user_settings.updated_at = datetime.utcnow()
    #     await db.commit()
    #     await db.refresh(user_settings)
    
    data["user_id"] = user_settings.user_id
    data["updated_at"] = user_settings.updated_at
    return data

async def create_or_update_settings(db: AsyncSession, user_id: str, settings: dict):
    """Update or create settings for a user"""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalars().first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=user_id)
        db.add(user_settings)
    
    # Update settings_json
    # We should merge with existing if partial update is needed, but typically settings update sends full payload or we want to overwrite.
    # The routes usage suggests model_dump(exclude_unset=True) so it might be partial.
    # If partial, we need to merge.
    
    current_data = user_settings.settings_json or {}
    current_data.update(settings)
    user_settings.settings_json = current_data
    
    # Explicitly touch updated_at (though onupdate might handle it, manual update ensures it changes even if content is same)
    user_settings.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user_settings)
    
    return await get_user_settings(db, user_id)

async def delete_user_settings(db: AsyncSession, user_id: str):
    """Delete settings for a user"""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalars().first()
    
    if user_settings:
        await db.delete(user_settings)
        await db.commit()
        return True
    return False
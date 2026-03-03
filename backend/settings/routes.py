# backend/settings/routes.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sql_database import get_db
from settings.models import get_user_settings, create_or_update_settings, delete_user_settings
from settings.schemas import SettingsUpdate, SettingsResponse
from auth.middleware import require_admin
from config import SUPPORTED_MODELS, DEFAULT_PAGES_PER_CHUNK
from datetime import datetime

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=SettingsResponse)
async def get_settings_route(admin_user = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """API endpoint to get the admin's settings."""
    user_id = str(admin_user.id)
    settings = await get_user_settings(db, user_id)
    
    if not settings:
        # Auto-create defaults if settings do not exist, to avoid 404
        default_settings = {
            "default_model_provider": "openai",
            "default_model_name": "gpt-4o",
            "temperature": 0.3,
            "max_output_tokens": 8192,
            "top_p": 0.95,
            "stop_sequences": [],
            "pages_per_chunk": DEFAULT_PAGES_PER_CHUNK,
            "comparison_chunk_size": 10,
            "max_comparison_chunks": 0
        }
        settings = await create_or_update_settings(db, user_id, default_settings)
    
    # Ensure a default value for pages_per_chunk if it's missing
    if "pages_per_chunk" not in settings:
        settings["pages_per_chunk"] = DEFAULT_PAGES_PER_CHUNK
        
    # datetime objects from SQLAlchemy are fine for Pydantic v2 usually, 
    # but existing code manually converts. Let's keep it safe.
    if 'updated_at' in settings and isinstance(settings['updated_at'], datetime):
        settings['updated_at'] = settings['updated_at'].isoformat()
    
    # Use model_validate which is the modern Pydantic v2 way
    return SettingsResponse.model_validate(settings)

@router.post("", response_model=SettingsResponse)
async def update_settings_route(
    settings_data: SettingsUpdate,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """API endpoint to create or update admin settings."""
    user_id = str(admin_user.id)
    # `exclude_unset=True` ensures we only update fields the user actually sent
    settings_dict = settings_data.model_dump(exclude_unset=True)
    
    updated_settings = await create_or_update_settings(db, user_id, settings_dict)
    
    if not updated_settings:
        raise HTTPException(status_code=500, detail="Failed to save settings to the database.")

    if 'updated_at' in updated_settings and isinstance(updated_settings['updated_at'], datetime):
        updated_settings['updated_at'] = updated_settings['updated_at'].isoformat()

    return SettingsResponse.model_validate(updated_settings)

@router.get("/models")
async def get_supported_models_route():
    """API endpoint to get the list of supported models for UI dropdowns."""
    return SUPPORTED_MODELS

@router.delete("")
async def remove_settings_route(admin_user = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """API endpoint to delete admin's settings."""
    user_id = str(admin_user.id)
    deleted = await delete_user_settings(db, user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="No settings found to delete.")
    
    return {"message": "Settings deleted successfully"}
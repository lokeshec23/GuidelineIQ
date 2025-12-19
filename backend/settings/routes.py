# backend/settings/routes.py

from fastapi import APIRouter, HTTPException, Depends
from settings.models import get_user_settings, create_or_update_settings, delete_user_settings
from settings.schemas import SettingsUpdate, SettingsResponse
from auth.middleware import require_admin
from config import SUPPORTED_MODELS, DEFAULT_PAGES_PER_CHUNK
from datetime import datetime
from utils.logger import log_settings_update, log_activity, LogOperation, LogLevel

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=SettingsResponse)
async def get_settings_route(admin_user: dict = Depends(require_admin)):
    """API endpoint to get the admin's settings."""
    user_id = str(admin_user["_id"])
    settings = await get_user_settings(user_id)
    
    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Settings not found. Please save your settings first."
        )
    
    # ✅ CORRECTED: Convert datetime to ISO string before validation
    if 'updated_at' in settings and isinstance(settings['updated_at'], datetime):
        settings['updated_at'] = settings['updated_at'].isoformat()
    
    # Ensure a default value for pages_per_chunk if it's missing
    if "pages_per_chunk" not in settings:
        settings["pages_per_chunk"] = DEFAULT_PAGES_PER_CHUNK
    
    # Use model_validate which is the modern Pydantic v2 way
    return SettingsResponse.model_validate(settings)

@router.post("", response_model=SettingsResponse)
async def update_settings_route(
    settings_data: SettingsUpdate,
    admin_user: dict = Depends(require_admin)
):
    """API endpoint to create or update admin settings."""
    user_id = str(admin_user["_id"])
    # `exclude_unset=True` ensures we only update fields the user actually sent
    settings_dict = settings_data.model_dump(exclude_unset=True)
    
    updated_settings = await create_or_update_settings(user_id, settings_dict)
    
    if not updated_settings:
        raise HTTPException(status_code=500, detail="Failed to save settings to the database.")

    # ✅ CORRECTED: Convert datetime to ISO string before validation
    if 'updated_at' in updated_settings and isinstance(updated_settings['updated_at'], datetime):
        updated_settings['updated_at'] = updated_settings['updated_at'].isoformat()
    
    # Log settings update
    updated_fields = list(settings_dict.keys())
    await log_settings_update(
        user_id=user_id,
        username=admin_user.get("email", "Admin"),
        updated_fields=updated_fields
    )

    return SettingsResponse.model_validate(updated_settings)

@router.get("/models")
async def get_supported_models_route():
    """API endpoint to get the list of supported models for UI dropdowns."""
    return SUPPORTED_MODELS

@router.delete("")
async def remove_settings_route(admin_user: dict = Depends(require_admin)):
    """API endpoint to delete admin's settings."""
    user_id = str(admin_user["_id"])
    deleted = await delete_user_settings(user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="No settings found to delete.")
    
    # Log settings deletion
    await log_activity(
        user_id=user_id,
        username=admin_user.get("email", "Admin"),
        operation=LogOperation.SETTINGS_DELETE,
        level=LogLevel.INFO
    )
    
    return {"message": "Settings deleted successfully"}
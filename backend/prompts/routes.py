from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict
from auth.middleware import get_current_user_id
from prompts.models import get_user_prompts, save_user_prompts, reset_user_prompts, get_default_prompts_from_db, get_default_prompts
from utils.logger import log_activity, LogOperation, LogLevel
import database
from bson import ObjectId


router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptsUpdate(BaseModel):
    ingest_prompts: Dict[str, Dict[str, str]]  # e.g., {"openai": {"system_prompt": "...", "user_prompt": "..."}, "gemini": {...}}
    compare_prompts: Dict[str, Dict[str, str]]  # e.g., {"openai": {"system_prompt": "...", "user_prompt": "..."}, "gemini": {...}}


@router.get("")
async def get_prompts(user_id: str = Depends(get_current_user_id)):
    """
    Get current user's prompts (creates with defaults if not exists).
    """
    try:
        prompts = await get_user_prompts(user_id)
        return prompts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompts: {str(e)}")


@router.get("/defaults")
async def get_default_prompts_endpoint(user_id: str = Depends(get_current_user_id)):
    """
    Get system default prompts from database (or config fallback).
    """
    try:
        db_defaults = await get_default_prompts_from_db()
        if db_defaults:
            return db_defaults
        else:
            # Fallback to config defaults
            return get_default_prompts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch default prompts: {str(e)}")


@router.put("")
async def update_prompts(
    prompts: PromptsUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update current user's prompts.
    """
    try:
        success = await save_user_prompts(user_id, prompts.dict())
        if success:
            # Log prompt update
            user = await database.users_collection.find_one({"_id": ObjectId(user_id)})
            username = user.get("email", "Unknown") if user else "Unknown"
            await log_activity(
                user_id=user_id,
                username=username,
                operation=LogOperation.PROMPT_UPDATE,
                level=LogLevel.INFO
            )
            return {"message": "Prompts updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update prompts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompts: {str(e)}")


@router.post("/reset")
async def reset_prompts(user_id: str = Depends(get_current_user_id)):
    """
    Reset current user's prompts to defaults (from database or config).
    """
    try:
        success = await reset_user_prompts(user_id)
        if success:
            # Return the reset prompts (from database or config fallback)
            prompts = await get_user_prompts(user_id)
            return prompts
        else:
            raise HTTPException(status_code=500, detail="Failed to reset prompts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset prompts: {str(e)}")

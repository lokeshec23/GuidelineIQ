from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sql_database import get_db
from auth.middleware import get_current_user # Updated import to get user object
from prompts.models import get_user_prompts, save_user_prompts, reset_user_prompts, get_default_prompts_from_db, get_default_prompts


router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptsUpdate(BaseModel):
    ingest_prompts: Dict[str, Dict[str, str]]  # e.g., {"openai": {"system_prompt": "...", "user_prompt": "..."}, "gemini": {...}}
    compare_prompts: Dict[str, Dict[str, str]]  # e.g., {"openai": {"system_prompt": "...", "user_prompt": "..."}, "gemini": {...}}


@router.get("")
async def get_prompts(
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's prompts (creates with defaults if not exists).
    """
    try:
        user_id = str(current_user.id)
        prompts = await get_user_prompts(db, user_id)
        return prompts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompts: {str(e)}")


@router.get("/defaults")
async def get_default_prompts_endpoint(
    db: AsyncSession = Depends(get_db)
    # No user dependency needed for public defaults? Or secure it? Original had user_id dep.
):
    """
    Get system default prompts from database (or config fallback).
    """
    try:
        db_defaults = await get_default_prompts_from_db(db)
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
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's prompts.
    """
    try:
        user_id = str(current_user.id)
        success = await save_user_prompts(db, user_id, prompts.dict())
        if success:
            return {"message": "Prompts updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update prompts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompts: {str(e)}")


@router.post("/reset")
async def reset_prompts(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset current user's prompts to defaults (from database or config).
    """
    try:
        user_id = str(current_user.id)
        success = await reset_user_prompts(db, user_id)
        if success:
            # Return the reset prompts (from database or config fallback)
            prompts = await get_user_prompts(db, user_id)
            return prompts
        else:
            raise HTTPException(status_code=500, detail="Failed to reset prompts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset prompts: {str(e)}")

# backend/prompts/routes.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict
from auth.middleware import get_current_user_id
from prompts.models import get_user_prompts, save_user_prompts, reset_user_prompts


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
            return {"message": "Prompts updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update prompts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompts: {str(e)}")


@router.post("/reset")
async def reset_prompts(user_id: str = Depends(get_current_user_id)):
    """
    Reset current user's prompts to defaults.
    """
    try:
        success = await reset_user_prompts(user_id)
        if success:
            # Return the reset prompts
            prompts = await get_user_prompts(user_id)
            return prompts
        else:
            raise HTTPException(status_code=500, detail="Failed to reset prompts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset prompts: {str(e)}")

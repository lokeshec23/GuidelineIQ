# backend/history/routes.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from history.models import (
    get_user_ingest_history,
    delete_ingest_history,
    get_user_compare_history,
    delete_compare_history
)
from history.schemas import IngestHistoryItem, CompareHistoryItem, DeleteResponse
from auth.middleware import get_current_user_from_token

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/ingest", response_model=List[IngestHistoryItem])
async def get_ingest_history(current_user: dict = Depends(get_current_user_from_token)):
    """Get logged-in user's ingest history"""
    user_id = str(current_user["_id"])
    history = await get_user_ingest_history(user_id)
    return history


@router.delete("/ingest/{record_id}", response_model=DeleteResponse)
async def delete_ingest_record(
    record_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Delete an ingest history record"""
    user_id = str(current_user["_id"])
    success = await delete_ingest_history(record_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    return DeleteResponse(message="Record deleted successfully", success=True)


# ✅ NEW: Compare history routes
@router.get("/compare", response_model=List[CompareHistoryItem])
async def get_compare_history(current_user: dict = Depends(get_current_user_from_token)):
    """Get logged-in user's compare history"""
    user_id = str(current_user["_id"])
    history = await get_user_compare_history(user_id)
    return history


@router.delete("/compare/{record_id}", response_model=DeleteResponse)
async def delete_compare_record(
    record_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Delete a compare history record"""
    user_id = str(current_user["_id"])
    success = await delete_compare_history(record_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    return DeleteResponse(message="Record deleted successfully", success=True)

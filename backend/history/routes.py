from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
from history.models import (
    get_user_ingest_history,
    delete_ingest_history,
    get_user_compare_history,
    delete_compare_history,
    delete_all_ingest_history,
    delete_all_compare_history
)
from history.schemas import IngestHistoryItem, CompareHistoryItem, DeleteResponse
from auth.middleware import get_current_user_from_token
from utils.gridfs_helper import get_pdf_from_gridfs
from bson import ObjectId
import database
import io

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


@router.delete("/ingest", response_model=DeleteResponse)
async def delete_all_ingest_records(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Delete all ingest history records for the user"""
    user_id = str(current_user["_id"])
    count = await delete_all_ingest_history(user_id)
    
    return DeleteResponse(message=f"Deleted {count} records successfully", success=True)


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


@router.delete("/compare", response_model=DeleteResponse)
async def delete_all_compare_records(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Delete all compare history records for the user"""
    user_id = str(current_user["_id"])
    count = await delete_all_compare_history(user_id)
    
    return DeleteResponse(message=f"Deleted {count} records successfully", success=True)


# ✅ NEW: Get list of PDFs for an ingest record
@router.get("/ingest/{record_id}/pdfs")
async def get_ingest_pdfs_list(
    record_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get list of all PDFs for an ingest record"""
    user_id = str(current_user["_id"])
    
    # Verify record exists and belongs to user
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=400, detail="Invalid record ID")
    
    from database import db_manager
    if db_manager.ingest_history is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    record = await db_manager.ingest_history.find_one({
        "_id": ObjectId(record_id),
        "user_id": user_id
    })
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    # ✅ Handle backward compatibility
    pdf_files = record.get("pdf_files", [])
    if not pdf_files and record.get("gridfs_file_id"):
        # Old record with single PDF - convert to new format
        pdf_files = [{
            "file_index": 0,
            "filename": record.get("uploaded_file", "document.pdf"),
            "gridfs_file_id": record.get("gridfs_file_id")
        }]
    
    return {"pdf_files": pdf_files}


# ✅ UPDATED: PDF viewer endpoint with support for multiple PDFs
@router.get("/ingest/{record_id}/pdf")
async def get_ingest_pdf(
    record_id: str,
    file_index: int = 0,  # ✅ NEW: Support fetching specific PDF by index
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get PDF file for an ingest record (supports multiple PDFs via file_index)"""
    user_id = str(current_user["_id"])
    
    # Verify record exists and belongs to user
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=400, detail="Invalid record ID")
    
    from database import db_manager
    if db_manager.ingest_history is None:
        # Fallback or error if DB not reachable (should ideally be connected via lifespan)
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    record = await db_manager.ingest_history.find_one({
        "_id": ObjectId(record_id),
        "user_id": user_id
    })
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    # ✅ NEW: Handle multiple PDFs
    pdf_files = record.get("pdf_files", [])
    gridfs_file_id = None
    filename = "document.pdf"
    
    if pdf_files:
        # New format: multiple PDFs
        if file_index >= len(pdf_files):
            raise HTTPException(status_code=404, detail=f"PDF index {file_index} not found")
        
        pdf_info = pdf_files[file_index]
        gridfs_file_id = pdf_info.get("gridfs_file_id")
        filename = pdf_info.get("filename", f"document_{file_index}.pdf")
    else:
        # Old format: single PDF (backward compatibility)
        gridfs_file_id = record.get("gridfs_file_id")
        filename = record.get("uploaded_file", "document.pdf")
    
    if not gridfs_file_id:
        raise HTTPException(status_code=404, detail="No PDF file associated with this record")
    
    try:
        # Get PDF from GridFS
        pdf_content = await get_pdf_from_gridfs(gridfs_file_id)
        
        # Escape double quotes to prevent header breaking
        filename = filename.replace('"', '\\"')

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )
    except Exception as e:
        print(f"❌ Error retrieving PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve PDF file")


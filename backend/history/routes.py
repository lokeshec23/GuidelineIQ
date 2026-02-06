from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sql_database import get_db
from history.models import (
    get_user_ingest_history,
    delete_ingest_history,
    get_user_compare_history,
    delete_compare_history,
    delete_all_ingest_history,
    delete_all_compare_history
)
from history.schemas import IngestHistoryItem, CompareHistoryItem, DeleteResponse
from auth.middleware import get_current_user_from_token, get_current_user
from models.sql_models import IngestHistory, File
import io

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/ingest", response_model=List[IngestHistoryItem])
async def get_ingest_history(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get logged-in user's ingest history"""
    user_id = str(current_user.id)
    history = await get_user_ingest_history(db, user_id)
    
    # Map SQLAlchemy model to Pydantic schema with camelCase
    return [
        IngestHistoryItem(
            id=str(h.id),
            user_id=h.user_id,
            username=h.username or "Unknown",
            investor=h.investor or "",
            version=h.version or "",
            uploadedFile=h.uploaded_file or "",
            extractedFile=h.extracted_file or "",
            created_at=h.created_at,
            effective_date=h.effective_date,
            expiry_date=h.expiry_date,
            preview_data=h.preview_data or [],
            pdf_files=h.pdf_files or []
        ) for h in history
    ]


@router.delete("/ingest/{record_id}", response_model=DeleteResponse)
async def delete_ingest_record(
    record_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an ingest history record"""
    user_id = str(current_user.id)
    success = await delete_ingest_history(db, record_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    return DeleteResponse(message="Record deleted successfully", success=True)


@router.delete("/ingest", response_model=DeleteResponse)
async def delete_all_ingest_records(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete all ingest history records for the user"""
    user_id = str(current_user.id)
    count = await delete_all_ingest_history(db, user_id)
    
    return DeleteResponse(message=f"Deleted {count} records successfully", success=True)


# ✅ NEW: Compare history routes
@router.get("/compare", response_model=List[CompareHistoryItem])
async def get_compare_history(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get logged-in user's compare history"""
    user_id = str(current_user.id)
    history = await get_user_compare_history(db, user_id)
    
    return [
        CompareHistoryItem(
            id=str(h.id),
            user_id=h.user_id,
            username=h.username or "Unknown",
            uploadedFile1=h.uploaded_file1 or "",
            uploadedFile2=h.uploaded_file2 or "",
            extractedFile=h.extracted_file or "",
            created_at=h.created_at,
            preview_data=h.preview_data or []
        ) for h in history
    ]


@router.delete("/compare/{record_id}", response_model=DeleteResponse)
async def delete_compare_record(
    record_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a compare history record"""
    user_id = str(current_user.id)
    success = await delete_compare_history(db, record_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    return DeleteResponse(message="Record deleted successfully", success=True)


@router.delete("/compare", response_model=DeleteResponse)
async def delete_all_compare_records(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete all compare history records for the user"""
    user_id = str(current_user.id)
    count = await delete_all_compare_history(db, user_id)
    
    return DeleteResponse(message=f"Deleted {count} records successfully", success=True)


# ✅ NEW: Get list of PDFs for an ingest record
@router.get("/ingest/{record_id}/pdfs")
async def get_ingest_pdfs_list(
    record_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of all PDFs for an ingest record"""
    user_id = str(current_user.id)
    
    result = await db.execute(
        select(IngestHistory).where(IngestHistory.id == record_id, IngestHistory.user_id == user_id)
    )
    record = result.scalars().first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    # ✅ Handle backward compatibility
    pdf_files = record.pdf_files or []
    if not pdf_files and record.gridfs_file_id:
        # Old record with single PDF - convert to new format
        pdf_files = [{
            "file_index": 0,
            "filename": record.uploaded_file or "document.pdf",
            "gridfs_file_id": record.gridfs_file_id
        }]
    
    return {"pdf_files": pdf_files}


# ✅ UPDATED: PDF viewer endpoint with support for multiple PDFs
@router.get("/ingest/{record_id}/pdf")
async def get_ingest_pdf(
    record_id: str,
    file_index: int = 0,  
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get PDF file for an ingest record (supports multiple PDFs via file_index)"""
    user_id = str(current_user.id)
    
    result = await db.execute(
        select(IngestHistory).where(IngestHistory.id == record_id, IngestHistory.user_id == user_id)
    )
    record = result.scalars().first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized")
    
    # ✅ NEW: Handle multiple PDFs
    pdf_files = record.pdf_files or []
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
        gridfs_file_id = record.gridfs_file_id
        filename = record.uploaded_file or "document.pdf"
    
    if not gridfs_file_id:
        raise HTTPException(status_code=404, detail="No PDF file associated with this record")
    
    try:
        # Get PDF from File table logic (Replacing GridFS)
        file_result = await db.execute(select(File).where(File.id == gridfs_file_id))
        file_record = file_result.scalars().first()
        
        if not file_record:
             raise HTTPException(status_code=404, detail="File content not found in database")
        
        pdf_content = file_record.content
        
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve PDF file")


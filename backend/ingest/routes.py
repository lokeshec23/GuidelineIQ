# backend/ingest/routes.py

import os
import uuid
import tempfile
import asyncio
import json
from bson import ObjectId
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import AsyncGenerator

# Local utilities
from ingest.schemas import IngestResponse, ProcessingStatus
from ingest.processor import process_guideline_background
from settings.models import get_user_settings
from auth.utils import verify_token
from utils.progress import update_progress, get_progress, delete_progress, progress_store, progress_lock
from history.models import check_duplicate_ingestion
from config import SUPPORTED_MODELS
from utils.json_to_excel import dynamic_json_to_excel
from utils.json_to_excel import dynamic_json_to_excel
from typing import List
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingest Guideline"])


# ✅ CORRECTED: Define the dependency function properly
async def get_current_user_id_from_token(authorization: str = Header(...)) -> str:
    """
    A FastAPI dependency that extracts and validates the user ID from a JWT
    token in the 'Authorization' header.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token does not contain a user ID")
        
    return user_id

@router.post("/guideline", response_model=IngestResponse)
async def ingest_guideline(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    investor: str = Form(None),
    version: str = Form(None),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    effective_date: str = Form(None),
    expiry_date: str = Form(None),
    page_range: str = Form(None),
    guideline_type: str = Form(None),
    program_type: str = Form(None),
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Endpoint to upload one or more PDFs and process them asynchronously.
    Returns the session_id immediately. Use SSE to track progress.
    """
    # Set defaults if not provided
    investor = investor or "Unknown Investor"
    version = version or "v1"
    
    # Validate all files are PDFs
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type for '{file.filename}'. Only PDF files are supported."
            )

    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")
    
    if model_name not in SUPPORTED_MODELS.get(model_provider, []):
        raise HTTPException(status_code=400, detail=f"Unsupported model '{model_name}' for '{model_provider}'")
    
    from database import db_manager
    if db_manager.users is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    admin_user = await db_manager.users.find_one({"role": "admin"})
    if not admin_user:
        raise HTTPException(
            status_code=500, 
            detail="System configuration error. No admin user found."
        )
    
    admin_settings = await get_user_settings(str(admin_user["_id"]))
    if not admin_settings:
        raise HTTPException(
            status_code=403, 
            detail="API keys not configured. Please contact the administrator to configure API keys."
        )

    current_user = await db_manager.users.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    if await check_duplicate_ingestion(investor, version, user_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Duplicate ingestion: Guidelines for Investor '{investor}' and Version '{version}' already exist."
        )

    session_id = str(uuid.uuid4())
    
    # Initialize progress
    update_progress(session_id, 0, "Initializing ingestion...")
    
    # Save multiple PDFs to GridFS
    gridfs_file_ids = []
    filenames = []
    
    try:
        from utils.gridfs_helper import save_pdf_to_gridfs
        
        for idx, file in enumerate(files):
            content = await file.read()
            
            gridfs_file_id = await save_pdf_to_gridfs(
                file_content=content,
                filename=file.filename,
                metadata={
                    "investor": investor,
                    "version": version,
                    "session_id": session_id,
                    "user_id": user_id,
                    "uploaded_by": current_user.get("email", "Unknown"),
                    "page_range": page_range,
                    "guideline_type": guideline_type,
                    "program_type": program_type,
                    "file_index": idx,
                    "total_files": len(files)
                }
            )
            gridfs_file_ids.append(gridfs_file_id)
            filenames.append(file.filename)
            
            gridfs_file_ids.append(gridfs_file_id)
            filenames.append(file.filename)
            
        logger.info(f"Stored {len(gridfs_file_ids)} PDF(s) in GridFS")
    except Exception as e:

        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {str(e)}")

    # Start background processing
    background_tasks.add_task(
        process_guideline_background,
        session_id=session_id,
        gridfs_file_ids=gridfs_file_ids,
        filenames=filenames,
        investor=investor,
        version=version,  
        user_settings=admin_settings,
        model_provider=model_provider,
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=user_id,
        username=current_user.get("email", "Unknown"),
        effective_date=effective_date,
        expiry_date=expiry_date,
        page_range=page_range,
        guideline_type=guideline_type,
        program_type=program_type,
    )
    
    return IngestResponse(
        status="processing", 
        message="Ingestion started", 
        session_id=session_id
    )


@router.get("/progress/{session_id}")
async def progress_stream(session_id: str):
    """Stream progress updates via Server-Sent Events"""
    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1
        retry_count = 0
        max_retries = 600
        
        max_retries = 600
        
        logger.info(f"SSE connected: {session_id[:8]}")
        
        while retry_count < max_retries:

            with progress_lock:
                progress_data = progress_store.get(session_id)
            
            if not progress_data:
                break
                
            current_progress = progress_data["progress"]
            
            if current_progress != last_progress:
                last_progress = current_progress
                yield f"data: {json.dumps(progress_data)}\n\n"
                retry_count = 0
            
            if progress_data.get("status") in ["completed", "failed", "cancelled"]:
                await asyncio.sleep(0.5)
                break
            
            await asyncio.sleep(0.5)
            retry_count += 1
        
            await asyncio.sleep(0.5)
            retry_count += 1
        
        logger.info(f"SSE closed: {session_id[:8]}")
    
    return StreamingResponse(

        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/status/{session_id}", response_model=ProcessingStatus)
async def get_status(session_id: str):
    """Get current ingestion status"""
    with progress_lock:
        if session_id not in progress_store:
            raise HTTPException(status_code=404, detail="Session not found")
        
        data = progress_store[session_id]
        
        return ProcessingStatus(
            status=data.get("status", "processing"),
            progress=data["progress"],
            message=data["message"],
            result_url=f"/ingest/download/{session_id}" if data.get("excel_path") else None
        )


@router.get("/preview/{session_id}")
async def get_preview(session_id: str):
    """Endpoint to get the JSON data for the frontend preview table."""
    # 1. Try to get from in-memory store (active/recent jobs)
    with progress_lock:
        session_data = progress_store.get(session_id)
        if session_data and "preview_data" in session_data:
            # Return both preview data and history_id if available
            response_data = {
                "data": session_data["preview_data"],
                "history_id": session_data.get("history_id")  # May be None if not yet saved
            }
            return JSONResponse(content=response_data)

    # 2. If not found, try to get from database (historical records)
    try:
        if ObjectId.is_valid(session_id):
            from database import db_manager
            if db_manager.ingest_history is not None:
                record = await db_manager.ingest_history.find_one({"_id": ObjectId(session_id)})
                if record and "preview_data" in record:
                    # When fetching from DB, the session_id IS the history_id
                    response_data = {
                        "data": record["preview_data"],
                        "history_id": str(record["_id"])
                    }
                    return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"Error fetching preview from DB: {e}")

    raise HTTPException(status_code=404, detail="Preview data not found or job is not complete.")



@router.get("/download/{session_id}")
async def download_result(session_id: str):
    """Endpoint to download the final Excel file."""
    
    # 1. Try to get from in-memory store (active/recent jobs)
    with progress_lock:
        session_data = progress_store.get(session_id)
        if session_data and "excel_path" in session_data:
            excel_path = session_data["excel_path"]
            filename = session_data.get("filename", "extraction.xlsx")

            if os.path.exists(excel_path):
                return FileResponse(
                    excel_path,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=filename
                )

    # 2. If not found in memory, try to regenerate from DB (historical records)
    if ObjectId.is_valid(session_id):
        from database import db_manager
        if db_manager.ingest_history is not None:
            record = await db_manager.ingest_history.find_one({"_id": ObjectId(session_id)})
            
            if record and "preview_data" in record:
                try:
                    # Generate temp Excel file
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    dynamic_json_to_excel(record["preview_data"], tmp.name)
                    
                    filename = f"{record.get('investor', 'Unknown')}_{record.get('version', 'v1')}.xlsx"
                    
                    return FileResponse(
                        tmp.name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename=filename
                    )
                except Exception as e:
                    logger.error(f"Error regenerating Excel from DB: {e}")
                    raise HTTPException(status_code=500, detail="Failed to regenerate Excel file")

    raise HTTPException(status_code=404, detail="Result file not found or already downloaded.")


def cleanup_file(path: str):
    """A simple background task to delete a file."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Cleaned up temporary file: {path}")
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")

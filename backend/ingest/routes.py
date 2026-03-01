# backend/ingest/routes.py

import os
import uuid
import tempfile
import asyncio
import json
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import AsyncGenerator, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sql_database import get_db
from models.sql_models import User, IngestHistory, CompareHistory # Import CompareHistory if needed

# Local utilities
from ingest.schemas import IngestResponse, ProcessingStatus
from ingest.processor import process_guideline_background
from settings.models import get_user_settings
from auth.utils import verify_token
# from auth.middleware import get_current_user # Used but we have custom dependency below?
from utils.progress import update_progress, get_progress, delete_progress, progress_store, progress_lock
from utils.progress import async_get_progress_data, async_get_session_data
from history.models import check_duplicate_ingestion
from config import SUPPORTED_MODELS
from utils.json_to_excel import dynamic_json_to_excel
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
    user_id: str = Depends(get_current_user_id_from_token),
    db: AsyncSession = Depends(get_db)
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
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type for '{file.filename}'. Only PDF files are supported."
            )

    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")
    
    if model_name not in SUPPORTED_MODELS.get(model_provider, []):
        raise HTTPException(status_code=400, detail=f"Unsupported model '{model_name}' for '{model_provider}'")
    
    # Check Admin Settings
    # Find admin user (Query DB)
    result = await db.execute(select(User).where(User.role == "admin").limit(1))
    admin_user = result.scalars().first()
    if not admin_user:
        result = await db.execute(select(User).where(User.is_admin == True).limit(1))
        admin_user = result.scalars().first()
        
    if not admin_user:
        raise HTTPException(
            status_code=500, 
            detail="System configuration error. No admin user found."
        )
    
    admin_settings = await get_user_settings(db, str(admin_user.id))
    if not admin_settings:
        raise HTTPException(
            status_code=403, 
            detail="API keys not configured. Please contact the administrator to configure API keys."
        )

    # Find Current User
    result_user = await db.execute(select(User).where(User.id == user_id))
    current_user = result_user.scalars().first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    if await check_duplicate_ingestion(db, investor, version, user_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Duplicate ingestion: Guidelines for Investor '{investor}' and Version '{version}' already exist."
        )

    session_id = str(uuid.uuid4())
    
    # Initialize progress
    update_progress(session_id, 0, "Initializing ingestion...")
    
    # Save multiple PDFs to SQL (via helper)
    gridfs_file_ids = []
    filenames = []
    
    try:
        from utils.gridfs_helper import save_pdf_to_gridfs
        
        for idx, file in enumerate(files):
            content = await file.read()
            
            # Helper renamed/updated to use SQL `File` table
            gridfs_file_id = await save_pdf_to_gridfs(
                db=db, # Pass DB session
                file_content=content,
                filename=file.filename,
                metadata={
                    "investor": investor,
                    "version": version,
                    "session_id": session_id,
                    "user_id": user_id,
                    "uploaded_by": current_user.email, # Use attribute
                    "page_range": page_range,
                    "guideline_type": guideline_type,
                    "program_type": program_type,
                    "file_index": idx,
                    "total_files": len(files)
                }
            )
            gridfs_file_ids.append(gridfs_file_id)
            filenames.append(file.filename)
            
        logger.info(f"Stored {len(gridfs_file_ids)} PDF(s) in Database")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {str(e)}")

    # Start background processing
    # NOTE: Background tasks run after dependency cleanup (session closing).
    # So process_guideline_background must create its OWN session.
    # We pass IDs (strings) which is safe.
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
        username=current_user.email,
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
        
        logger.info(f"SSE connected: {session_id[:8]}")
        
        while retry_count < max_retries:
            # Use async-safe progress access (does NOT block the event loop)
            progress_data = await async_get_progress_data(session_id)
            
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
    data = await async_get_progress_data(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return ProcessingStatus(
        status=data.get("status", "processing"),
        progress=data["progress"],
        message=data["message"],
        result_url=f"/ingest/download/{session_id}" if data.get("excel_path") else None
    )


@router.get("/preview/{session_id}")
async def get_preview(session_id: str, db: AsyncSession = Depends(get_db)):
    """Endpoint to get the JSON data for the frontend preview table."""
    # 1. Try to get from in-memory store (active/recent jobs) — async-safe
    session_data = await async_get_session_data(session_id)
    if session_data and "preview_data" in session_data:
        response_data = {
            "data": session_data["preview_data"],
            "history_id": session_data.get("history_id")
        }
        return JSONResponse(content=response_data)

    # 2. If not found, try to get from database (historical records)
    try:
        # Query DB using session_id as Primary Key (if ID match) or query by something else?
        # IngestHistory id is UUID (String). session_id is also UUID.
        # If accessing by historical session, session_id == id.
        
        result = await db.execute(select(IngestHistory).where(IngestHistory.id == session_id))
        record = result.scalars().first()
        
        if record and record.preview_data:
             response_data = {
                 "data": record.preview_data, # JSON field
                 "history_id": str(record.id)
             }
             return JSONResponse(content=response_data)
             
    except Exception as e:
        logger.error(f"Error fetching preview from DB: {e}", exc_info=True)

    raise HTTPException(status_code=404, detail="Preview data not found or job is not complete.")



@router.get("/download/{session_id}")
async def download_result(session_id: str, db: AsyncSession = Depends(get_db)):
    """Endpoint to download the final Excel file."""
    
    # 1. Try to get from in-memory store (active/recent jobs) — async-safe
    session_data = await async_get_session_data(session_id)
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
    # Check DB
    try:
         result = await db.execute(select(IngestHistory).where(IngestHistory.id == session_id))
         record = result.scalars().first()

         if record and record.preview_data:
            try:
                # Generate temp Excel file
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                # Match frontend hidden columns
                hidden_columns = ['Classification', 'Notes', '_verification', 'key', 'PPE_Field_Type']
                dynamic_json_to_excel(record.preview_data, tmp.name, hidden_columns=hidden_columns)
                
                filename = f"{record.investor or 'Unknown'}_{record.version or 'v1'}.xlsx"
                
                return FileResponse(
                    tmp.name,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=filename
                )
            except Exception as e:
                logger.error(f"Error regenerating Excel from DB: {e}")
                raise HTTPException(status_code=500, detail="Failed to regenerate Excel file")
                
    except Exception as e:
         logger.error(f"Error fetching result from DB: {e}")

    raise HTTPException(status_code=404, detail="Result file not found or already downloaded.")


def cleanup_file(path: str):
    """A simple background task to delete a file."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Cleaned up temporary file: {path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {path}: {e}")


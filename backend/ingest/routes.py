# backend/ingest/routes.py

import os
import uuid
import tempfile
import json
import asyncio
from typing import AsyncGenerator
from bson import ObjectId
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

# Local utilities
from ingest.schemas import IngestResponse, ProcessingStatus
from ingest.processor import process_guideline_background
from settings.models import get_user_settings
from auth.utils import verify_token
from utils.progress import update_progress, get_progress, delete_progress, progress_store, progress_lock
from history.models import check_duplicate_ingestion
from config import SUPPORTED_MODELS
from utils.json_to_excel import dynamic_json_to_excel
from typing import List

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
    investor: str = Form(...),
    version: str = Form(...),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    effective_date: str = Form(...),
    expiry_date: str = Form(None),
    page_range: str = Form(None),
    guideline_type: str = Form(None),
    program_type: str = Form(None),
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Endpoint to upload one or more PDFs and start the ingestion background process.
    """
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
    
    # ✅ UPDATED: Fetch admin's settings instead of current user's
    # ✅ UPDATED: Fetch admin's settings instead of current user's
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

    # ✅ NEW: Get current user's info for history tracking
    current_user = await db_manager.users.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ NEW: Check for duplicate ingestion
    if await check_duplicate_ingestion(investor, version, user_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Duplicate ingestion: Guidelines for Investor '{investor}' and Version '{version}' already exist."
        )

    session_id = str(uuid.uuid4())
    
    # ✅ UPDATED: Save multiple PDFs to GridFS
    gridfs_file_ids = []
    filenames = []
    
    try:
        # Import GridFS helper
        from utils.gridfs_helper import save_pdf_to_gridfs
        
        for idx, file in enumerate(files):
            content = await file.read()
            
            # Save to GridFS with metadata
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
                    "file_index": idx,  # Track order of files
                    "total_files": len(files)
                }
            )
            gridfs_file_ids.append(gridfs_file_id)
            filenames.append(file.filename)
            
        print(f"✅ Stored {len(gridfs_file_ids)} PDF(s) in GridFS")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {str(e)}")

    update_progress(session_id, 0, "Initializing...")
    
    background_tasks.add_task(
        process_guideline_background,
        session_id=session_id,
        gridfs_file_ids=gridfs_file_ids,  # ✅ Pass list of GridFS IDs
        filenames=filenames,  # ✅ Pass list of filenames
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
    
    return IngestResponse(status="processing", message="Processing started", session_id=session_id)


@router.get("/progress/{session_id}")
async def progress_stream(session_id: str):
    """Streams processing progress using Server-Sent Events (SSE)."""
    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1
        try:
            while True:
                with progress_lock:
                    progress_data = progress_store.get(session_id)

                if not progress_data:
                    # Send a final message before closing
                    yield f"data: {json.dumps({'status': 'not_found', 'message': 'Session not found'})}\n\n"
                    break

                current_progress = progress_data["progress"]
                if current_progress != last_progress:
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    last_progress = current_progress

                if progress_data.get("status") in ["completed", "failed", "cancelled"]:
                    break
                
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            print(f"⚠️ SSE connection cancelled for session: {session_id[:8]}")
            raise
        except Exception as e:
            print(f"❌ SSE error for session {session_id[:8]}: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        finally:
            print(f"🔌 SSE connection closed for session: {session_id[:8]}")

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
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
        print(f"Error fetching preview from DB: {e}")

    raise HTTPException(status_code=404, detail="Preview data not found or job is not complete.")


@router.get("/download/{session_id}")
async def download_result(session_id: str, background_tasks: BackgroundTasks):
    """Endpoint to download the final Excel file and trigger cleanup."""
    
    # 1. Try to get from in-memory store (active/recent jobs)
    with progress_lock:
        session_data = progress_store.get(session_id)
        if session_data and "excel_path" in session_data:
            excel_path = session_data["excel_path"]
            filename = session_data.get("filename", "extraction.xlsx")

            if os.path.exists(excel_path):
                # Prevent re-downloads by removing session from store immediately
                del progress_store[session_id]
                background_tasks.add_task(cleanup_file, path=excel_path)
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
                    
                    background_tasks.add_task(cleanup_file, path=tmp.name)
                    
                    return FileResponse(
                        tmp.name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename=filename
                    )
                except Exception as e:
                    print(f"Error regenerating Excel from DB: {e}")
                    raise HTTPException(status_code=500, detail="Failed to regenerate Excel file")

    raise HTTPException(status_code=404, detail="Result file not found or already downloaded.")

def cleanup_file(path: str):
    """A simple background task to delete a file."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"🧹 Cleaned up temporary file: {path}")
    except Exception as e:
        print(f"❌ Error during file cleanup: {e}")
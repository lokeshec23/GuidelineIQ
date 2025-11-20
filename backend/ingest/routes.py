# backend/ingest/routes.py

import os
import uuid
import tempfile
import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

# Local utilities
from ingest.schemas import IngestResponse, ProcessingStatus
from ingest.processor import process_guideline_background
from settings.models import get_user_settings
from auth.utils import verify_token
from auth.middleware import get_admin_user
from utils.progress import update_progress, get_progress, delete_progress, progress_store, progress_lock
from config import SUPPORTED_MODELS

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
    file: UploadFile = File(...),
    investor: str = Form(...),
    version: str = Form(...),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Endpoint to upload a PDF and start the ingestion background process.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are supported.")

    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")
    
    if model_name not in SUPPORTED_MODELS.get(model_provider, []):
        raise HTTPException(status_code=400, detail=f"Unsupported model '{model_name}' for '{model_provider}'")
    
    # ✅ UPDATED: Fetch admin's settings instead of current user's
    admin_user = await get_admin_user()
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

    session_id = str(uuid.uuid4())
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            pdf_path = tmp_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    update_progress(session_id, 0, "Initializing...")
    
    background_tasks.add_task(
        process_guideline_background,
        session_id=session_id,
        pdf_path=pdf_path,
        filename=file.filename,
        investor=investor,
        version=version,  
        user_settings=admin_settings,  # ✅ UPDATED: Use admin's settings
        model_provider=model_provider,
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    
    return IngestResponse(status="processing", message="Processing started", session_id=session_id)


@router.get("/progress/{session_id}")
async def progress_stream(session_id: str):
    """Streams processing progress using Server-Sent Events (SSE)."""
    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1
        while True:
            with progress_lock:
                progress_data = progress_store.get(session_id)

            if not progress_data:
                break

            current_progress = progress_data["progress"]
            if current_progress != last_progress:
                # ✅ FIXED: Use proper newlines instead of escaped backslashes
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_progress = current_progress

            if progress_data.get("status") in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(0.5)
        
        print(f"🔌 SSE connection closed for session: {session_id[:8]}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/preview/{session_id}")
async def get_preview(session_id: str):
    """Endpoint to get the JSON data for the frontend preview table."""
    with progress_lock:
        session_data = progress_store.get(session_id)
        if not session_data or "preview_data" not in session_data:
            raise HTTPException(status_code=404, detail="Preview data not found or job is not complete.")
        return JSONResponse(content=session_data["preview_data"])


@router.get("/download/{session_id}")
async def download_result(session_id: str, background_tasks: BackgroundTasks):
    """Endpoint to download the final Excel file and trigger cleanup."""
    with progress_lock:
        session_data = progress_store.get(session_id)
        if not session_data or "excel_path" not in session_data:
            raise HTTPException(status_code=404, detail="Result file not found or already downloaded.")
        
        excel_path = session_data["excel_path"]
        filename = session_data.get("filename", "extraction.xlsx")

        if not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail="Result file has been cleaned up or does not exist.")
            
        # Prevent re-downloads by removing session from store immediately
        del progress_store[session_id]

    background_tasks.add_task(cleanup_file, path=excel_path)
    
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

def cleanup_file(path: str):
    """A simple background task to delete a file."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"🧹 Cleaned up temporary file: {path}")
    except Exception as e:
        print(f"❌ Error during file cleanup: {e}")
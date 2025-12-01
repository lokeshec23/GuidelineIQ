# backend/compare/routes.py
import os
import uuid
import tempfile
import json
from bson import ObjectId
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks, HTTPException, Depends, Header
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from compare.schemas import CompareResponse, ComparisonStatus, CompareFromDBRequest
from compare.processor import process_comparison_background
from settings.models import get_user_settings
from auth.utils import verify_token
# from auth.middleware import get_admin_user
from utils.progress import get_progress, delete_progress, progress_store, progress_lock
from config import SUPPORTED_MODELS
import asyncio
from typing import AsyncGenerator
from utils.json_to_excel import dynamic_json_to_excel

router = APIRouter(prefix="/compare", tags=["Compare Guidelines"])

async def get_current_user_id_from_token(authorization: str = Header(...)) -> str:
    """Extract and validate user ID from JWT token"""
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

@router.post("/guidelines", response_model=CompareResponse)
async def compare_guidelines(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Upload two Excel files and compare them using LLM"""
    
    print(f"Comparison request received:")
    print(f"  - File 1: {file1.filename}")
    print(f"  - File 2: {file2.filename}")
    print(f"  - Provider: {model_provider}")
    print(f"  - Model: {model_name}")
    print(f"  - User ID: {user_id}")
    
    # Validate model
    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")

    if model_name not in SUPPORTED_MODELS[model_provider]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{model_name}' for provider '{model_provider}'"
        )
    
    # Fetch admin's settings
    from database import users_collection
    admin_user = await users_collection.find_one({"role": "admin"})
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
    
    # Validate file types
    for file in [file1, file2]:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail=f"Only Excel files (.xlsx, .xls) are supported. Got: {file.filename}"
            )
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    print(f"\n{'='*60}")
    print(f"Session: {session_id}")
    print(f"{'='*60}\n")
    
    # Save Excel files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp1:
        content1 = await file1.read()
        tmp1.write(content1)
        file1_path = tmp1.name
        print(f"File 1 saved: {len(content1) / 1024:.2f} KB")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp2:
        content2 = await file2.read()
        tmp2.write(content2)
        file2_path = tmp2.name
        print(f"File 2 saved: {len(content2) / 1024:.2f} KB")
    
    # ✅ NEW: Get current user's info for history tracking
    current_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Initialize progress
    from utils.progress import update_progress
    update_progress(session_id, 0, "Starting comparison...")
    
    # Start background processing
    background_tasks.add_task(
        process_comparison_background,
        session_id=session_id,
        file1_path=file1_path,
        file2_path=file2_path,
        file1_name=file1.filename,
        file2_name=file2.filename,
        user_settings=admin_settings,
        model_provider=model_provider,
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=user_id,  # ✅ NEW: Pass user_id for history
        username=current_user.get("email", "Unknown"),  # ✅ NEW: Pass username for history
    )
    
    return CompareResponse(
        status="processing",
        message="Comparison started",
        session_id=session_id
    )


@router.post("/from-db", response_model=CompareResponse)
async def compare_from_db(
    request: CompareFromDBRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """Compare two guidelines selected from ingestion history"""
    
    if len(request.ingest_ids) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 guidelines must be selected for comparison")

    # Fetch history records
    from database import ingest_history_collection, users_collection
    
    records = []
    for record_id in request.ingest_ids:
        record = await ingest_history_collection.find_one({
            "_id": ObjectId(record_id),
            "user_id": user_id
        })
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
        records.append(record)

    # Generate temp Excel files from preview_data
    from utils.json_to_excel import dynamic_json_to_excel
    from utils.progress import update_progress
    
    file_paths = []
    file_names = []
    
    try:
        for record in records:
            preview_data = record.get("preview_data", [])
            if not preview_data:
                raise HTTPException(status_code=400, detail=f"No data found for record {record['_id']}")
            
            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            dynamic_json_to_excel(preview_data, tmp.name)
            file_paths.append(tmp.name)
            
            # Construct filename
            investor = record.get("investor", "Unknown")
            version = record.get("version", "v1")
            file_names.append(f"{investor}_{version}.xlsx")
            
    except Exception as e:
        # Cleanup on error
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)
        raise HTTPException(status_code=500, detail=f"Failed to prepare files: {str(e)}")

    # Fetch admin settings
    from database import users_collection
    admin_user = await users_collection.find_one({"role": "admin"})
    if not admin_user:
        raise HTTPException(status_code=500, detail="System configuration error")
        
    admin_settings = await get_user_settings(str(admin_user["_id"]))
    if not admin_settings:
        raise HTTPException(status_code=403, detail="API keys not configured")

    # Get current user info
    current_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    
    # Start processing
    session_id = str(uuid.uuid4())
    update_progress(session_id, 0, "Initializing from DB...")
    
    background_tasks.add_task(
        process_comparison_background,
        session_id=session_id,
        file1_path=file_paths[0],
        file2_path=file_paths[1],
        file1_name=file_names[0],
        file2_name=file_names[1],
        user_settings=admin_settings,
        model_provider=request.model_provider,
        model_name=request.model_name,
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        user_id=user_id,
        username=current_user.get("email", "Unknown"),
    )
    
    return CompareResponse(
        status="processing",
        message="Comparison started from DB",
        session_id=session_id
    )


@router.get("/progress/{session_id}")
async def progress_stream(session_id: str):
    """Stream progress updates via Server-Sent Events"""
    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1
        retry_count = 0
        max_retries = 600
        
        print(f"SSE connected: {session_id[:8]}")
        
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
        
        print(f"SSE closed: {session_id[:8]}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/status/{session_id}", response_model=ComparisonStatus)
async def get_status(session_id: str):
    """Get current comparison status"""
    with progress_lock:
        if session_id not in progress_store:
            raise HTTPException(status_code=404, detail="Session not found")
        
        data = progress_store[session_id]
        
        return ComparisonStatus(
            status=data.get("status", "processing"),
            progress=data["progress"],
            message=data["message"],
            result_url=f"/compare/download/{session_id}" if data.get("excel_path") else None
        )


@router.get("/preview/{session_id}")
async def get_preview(session_id: str):
    """Get JSON preview data"""
    with progress_lock:
        session_data = progress_store.get(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found or already downloaded")
            
        preview_data = session_data.get("preview_data")
        
        if not preview_data:
            raise HTTPException(status_code=404, detail="Preview data not available yet")
        
        return JSONResponse(content=preview_data)


@router.get("/download/{session_id}")
async def download_result(session_id: str, background_tasks: BackgroundTasks):
    """Download the comparison Excel file and cleanup"""
    
    # 1. Try to get from in-memory store
    with progress_lock:
        session_data = progress_store.get(session_id)
        if session_data and "excel_path" in session_data:
            excel_path = session_data["excel_path"]
            filename = session_data.get("filename", f"comparison_{session_id[:8]}.xlsx")
            
            if os.path.exists(excel_path):
                del progress_store[session_id]
                background_tasks.add_task(cleanup_file, path=excel_path)
                return FileResponse(
                    excel_path,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=filename,
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )

    # 2. If not found in memory, try to regenerate from DB (historical records)
    if ObjectId.is_valid(session_id):
        from database import compare_history_collection
        record = await compare_history_collection.find_one({"_id": ObjectId(session_id)})
        
        if record and "preview_data" in record:
            try:
                # Generate temp Excel file
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                dynamic_json_to_excel(record["preview_data"], tmp.name)
                
                filename = f"comparison_{session_id[:8]}.xlsx"
                
                background_tasks.add_task(cleanup_file, path=tmp.name)
                
                return FileResponse(
                    tmp.name,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=filename,
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )
            except Exception as e:
                print(f"Error regenerating Excel from DB: {e}")
                raise HTTPException(status_code=500, detail="Failed to regenerate Excel file")

    raise HTTPException(
        status_code=404, 
        detail="Session not found. The file might have already been downloaded or the session expired."
    )


def cleanup_file(path: str):
    """Background task to delete a file after download"""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"Cleaned up temporary file: {path}")
    except Exception as e:
        print(f"Error during file cleanup: {e}")
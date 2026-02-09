import os
import uuid
import tempfile
import json
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from compare.schemas import CompareResponse, ComparisonStatus, CompareFromDBRequest
from compare.processor import process_comparison_background
from compare.qdrant_compare_processor import process_qdrant_comparison_background
from compare.dscr_template_processor import process_dscr_template_comparison
from settings.models import get_user_settings
from auth.middleware import get_current_user
from models.sql_models import User, IngestHistory, CompareHistory
from sql_database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from utils.progress import get_progress, delete_progress, progress_store, progress_lock
from config import SUPPORTED_MODELS
import asyncio
from typing import AsyncGenerator
from utils.json_to_excel import dynamic_json_to_excel
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/compare", tags=["Compare Guidelines"])

@router.post("/guidelines", response_model=CompareResponse)
async def compare_guidelines(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload two Excel files and compare them using LLM"""
    
    logger.info(f"Comparison request received: File1={file1.filename}, File2={file2.filename}, Provider={model_provider}, Model={model_name}, UserID={current_user.id}")

    # Validate model
    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")

    if model_name not in SUPPORTED_MODELS[model_provider]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{model_name}' for provider '{model_provider}'"
        )
    
    # Fetch admin's settings
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
            detail="API keys not configured. Please contact the administrator."
        )
    
    # Validate file types
    for file in [file1, file2]:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            logger.warning(f"Invalid file type for comparison: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Only Excel files (.xlsx, .xls) are supported. Got: {file.filename}"
            )

    # Generate session ID
    session_id = str(uuid.uuid4())
    logger.info(f"Session: {session_id}")

    # Save Excel files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp1:
        content1 = await file1.read()
        tmp1.write(content1)
        file1_path = tmp1.name
        logger.info(f"File 1 saved: {len(content1) / 1024:.2f} KB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp2:
        content2 = await file2.read()
        tmp2.write(content2)
        file2_path = tmp2.name
        logger.info(f"File 2 saved: {len(content2) / 1024:.2f} KB")

    # Initialize progress
    from utils.progress import update_progress
    update_progress(session_id, 0, "Starting comparison...")
    
    # Start background processing
    background_tasks.add_task(
        process_dscr_template_comparison,
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
        user_id=str(current_user.id),
        username=current_user.email or "Unknown",
    )
    
    return CompareResponse(
        status="processing",
        message="Comparison started",
        session_id=session_id
    )

@router.post("/qdrant", response_model=CompareResponse)
async def compare_with_qdrant(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    investor: str = Form(None),
    version: str = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload two Excel files and compare them using Qdrant vector search."""
    
    logger.info(f"Qdrant comparison request: File1={file1.filename}, File2={file2.filename}, UserID={current_user.id}")
    
    # Validate file types
    for file in [file1, file2]:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            logger.warning(f"Invalid file type for Qdrant comparison: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Only Excel files (.xlsx, .xls) are supported. Got: {file.filename}"
            )
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    logger.info(f"Qdrant comparison session: {session_id}")
    
    # Save Excel files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp1:
        content1 = await file1.read()
        tmp1.write(content1)
        file1_path = tmp1.name
        logger.info(f"File 1 saved: {len(content1) / 1024:.2f} KB")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp2:
        content2 = await file2.read()
        tmp2.write(content2)
        file2_path = tmp2.name
        logger.info(f"File 2 saved: {len(content2) / 1024:.2f} KB")
    
    # Set defaults if not provided
    investor = investor or "Unknown Investor"
    version = version or "v1"
    
    # Initialize progress
    from utils.progress import update_progress
    update_progress(session_id, 0, "Starting Qdrant comparison...")
    
    # Start background processing
    background_tasks.add_task(
        process_qdrant_comparison_background,
        session_id=session_id,
        file1_path=file1_path,
        file2_path=file2_path,
        file1_name=file1.filename,
        file2_name=file2.filename,
        investor=investor,
        version=version,
        user_id=str(current_user.id),
        username=current_user.email or "Unknown",
    )
    
    return CompareResponse(
        status="processing",
        message="Qdrant comparison started",
        session_id=session_id
    )

@router.post("/dscr-template", response_model=CompareResponse)
async def compare_with_dscr_template(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare two DSCR guideline Excel files using the DSCR_GUIDELINES template."""
    
    logger.info(f"DSCR Template comparison request: File1={file1.filename}, File2={file2.filename}, Provider={model_provider}, Model={model_name}, UserID={current_user.id}")

    # Validate model
    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")

    if model_name not in SUPPORTED_MODELS[model_provider]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{model_name}' for provider '{model_provider}'"
        )
    
    # Fetch admin's settings
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
            detail="API keys not configured. Please contact the administrator."
        )
    
    # Validate file types
    for file in [file1, file2]:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            logger.warning(f"Invalid file type for DSCR comparison: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Only Excel files (.xlsx, .xls) are supported. Got: {file.filename}"
            )

    # Generate session ID
    session_id = str(uuid.uuid4())
    logger.info(f"DSCR Template comparison session: {session_id}")

    # Save Excel files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp1:
        content1 = await file1.read()
        tmp1.write(content1)
        file1_path = tmp1.name
        logger.info(f"File 1 saved: {len(content1) / 1024:.2f} KB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp2:
        content2 = await file2.read()
        tmp2.write(content2)
        file2_path = tmp2.name
        logger.info(f"File 2 saved: {len(content2) / 1024:.2f} KB")

    # Initialize progress
    from utils.progress import update_progress
    update_progress(session_id, 0, "Starting DSCR template comparison...")
    
    # Start background processing with DSCR template processor
    background_tasks.add_task(
        process_dscr_template_comparison,
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
        user_id=str(current_user.id),
        username=current_user.email or "Unknown",
    )
    
    return CompareResponse(
        status="processing",
        message="DSCR template comparison started",
        session_id=session_id
    )

@router.post("/from-db", response_model=CompareResponse)
async def compare_from_db(
    request: CompareFromDBRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare two guidelines selected from ingestion history"""
    
    if len(request.ingest_ids) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 guidelines must be selected for comparison")

    # Fetch history records
    records = []
    for record_id in request.ingest_ids:
        result = await db.execute(select(IngestHistory).where(
            IngestHistory.id == record_id,
            IngestHistory.user_id == str(current_user.id)
        ))
        record = result.scalars().first()
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
            preview_data = record.preview_data or []
            if not preview_data:
                raise HTTPException(status_code=400, detail=f"No data found for record {record.id}")
            
            # Create temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            dynamic_json_to_excel(preview_data, tmp.name)
            file_paths.append(tmp.name)
            
            # Construct filename
            investor = record.investor or "Unknown"
            version = record.version or "v1"
            file_names.append(f"{investor}_{version}.xlsx")
            
    except Exception as e:
        # Cleanup on error
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)
        raise HTTPException(status_code=500, detail=f"Failed to prepare files: {str(e)}")

    # Fetch admin settings
    result = await db.execute(select(User).where(User.role == "admin").limit(1))
    admin_user = result.scalars().first()
    
    if not admin_user:
        result = await db.execute(select(User).where(User.is_admin == True).limit(1))
        admin_user = result.scalars().first()

    if not admin_user:
        raise HTTPException(status_code=500, detail="System configuration error")
        
    admin_settings = await get_user_settings(db, str(admin_user.id))
    if not admin_settings:
        raise HTTPException(status_code=403, detail="API keys not configured")

    # Start processing
    session_id = str(uuid.uuid4())
    update_progress(session_id, 0, "Initializing from DB...")
    
    # Start background processing
    background_tasks.add_task(
        process_dscr_template_comparison,
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
        user_id=str(current_user.id),
        username=current_user.email or "Unknown",
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
async def download_result(session_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
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
                    filename=filename
                )

    # 2. If not found in memory, try to regenerate from DB (historical records)
    try:
        result = await db.execute(select(CompareHistory).where(CompareHistory.id == session_id))
        record = result.scalars().first()
        
        # Fallback for old sessions that used session_id instead of primary key
        if not record:
            result = await db.execute(select(CompareHistory).where(CompareHistory.session_id == session_id))
            record = result.scalars().first()
        
        if record and record.preview_data:
            # Generate temp Excel file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            preview_data = record.preview_data

            # Check if this is a DSCR Template Comparison (based on structure)
            is_dscr_template = False
            if preview_data and len(preview_data) > 0:
                 if "dscr_parameters" in preview_data[0]:
                     is_dscr_template = True

            if is_dscr_template:
                from compare.dscr_template_processor import (
                    DSCR_EXPORT_HEADER_MAP,
                    DSCR_EXPORT_COLUMN_ORDER,
                    DSCR_EXPORT_HIDDEN_COLUMNS
                )
                dynamic_json_to_excel(
                    preview_data,
                    tmp.name,
                    header_map=DSCR_EXPORT_HEADER_MAP,
                    hidden_columns=DSCR_EXPORT_HIDDEN_COLUMNS,
                    column_order=DSCR_EXPORT_COLUMN_ORDER
                )
            else:
                dynamic_json_to_excel(preview_data, tmp.name)
            
            # Construct filename
            filename = f"comparison_{session_id[:8]}.xlsx"
            if record.uploaded_file1 and record.uploaded_file2:
                filename = f"comparison_{record.uploaded_file1}_vs_{record.uploaded_file2}.xlsx"
            
            background_tasks.add_task(cleanup_file, path=tmp.name)
            
            return FileResponse(
                tmp.name,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=filename
            )
    except Exception as e:
        logger.error(f"Error regenerating Excel from DB: {e}")
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
            logger.info(f"Cleaned up temporary file: {path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {path}: {e}")

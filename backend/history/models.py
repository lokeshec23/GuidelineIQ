# backend/history/models.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, desc
from models.sql_models import IngestHistory, CompareHistory
from typing import List, Dict
from datetime import datetime

async def save_ingest_history(db: AsyncSession, data: dict) -> str:
    """Save ingest job to history"""
    
    # Clean data keys to match model
    model_data = {
        "user_id": data["user_id"],
        "username": data.get("username", "Unknown"),
        "investor": data["investor"],
        "version": data["version"],
        "uploaded_file": data["uploaded_file"],
        "extracted_file": data["extracted_file"],
        "preview_data": data.get("preview_data", []),
        "effective_date": data.get("effective_date"),
        "expiry_date": data.get("expiry_date"),
        "gridfs_file_id": data.get("gridfs_file_id"),  
        "pdf_files": data.get("pdf_files", []), 
        "created_at": datetime.utcnow()
    }
    
    # Add optional keys if present
    if "page_range" in data: model_data["page_range"] = data["page_range"]
    if "guideline_type" in data: model_data["guideline_type"] = data["guideline_type"]
    if "program_type" in data: model_data["program_type"] = data["program_type"]
    
    history_entry = IngestHistory(**model_data)
    db.add(history_entry)
    await db.commit()
    await db.refresh(history_entry)
    
    print(f"✅ Saved ingest history: {history_entry.id}")
    return str(history_entry.id)

async def get_user_ingest_history(db: AsyncSession, user_id: str) -> List[IngestHistory]:
    """Fetch user's ingest history sorted by most recent first"""
    result = await db.execute(
        select(IngestHistory)
        .where(IngestHistory.user_id == user_id)
        .order_by(desc(IngestHistory.created_at))
    )
    history = result.scalars().all()
    
    # Post-process for backward compatibility (converting old structure to new)
    # SQLAlchemy objects are mutable, but changes here won't persist unless commited.
    # We just want to ensure 'pdf_files' is populated for response.
    # The JSON column handles deserialization.
    
    # We will let the route/schema handle serialization, 
    # but the logic for "old record with single PDF" needs to be handled somewhere.
    # Ideally in the Pydantic schema validator or here by returning a list of dicts.
    # Returning objects is cleaner if we fix the data presentation layer.
    
    processed_history = []
    for doc in history:
        # Clone attributes to not mess with DB session object state if unnecessary
        # OR just attach a property.
        # Let's populate the object's pdf_files if missing and gridfs_id exists, 
        # but treating it as a transient fix.
        
        pdf_files = doc.pdf_files or []
        if not pdf_files and doc.gridfs_file_id:
             pdf_files = [{
                "file_index": 0,
                "filename": doc.uploaded_file or "document.pdf",
                "gridfs_file_id": doc.gridfs_file_id
            }]
        # We can assign it back to the object temporarily or return a wrapper
        doc.pdf_files = pdf_files 
        processed_history.append(doc)

    return processed_history

async def save_compare_history(db: AsyncSession, data: dict) -> str:
    """Save comparison job to history"""
    history_data = {
        "user_id": data["user_id"],
        "username": data.get("username", "Unknown"),
        "session_id": data.get("session_id"), 
        "investor": data.get("investor", "Unknown Investor"),
        "version": data.get("version", "v1"),
        "uploaded_file1": data["uploaded_file1"],
        "uploaded_file2": data["uploaded_file2"],
        "extracted_file": data["extracted_file"],
        "preview_data": data.get("preview_data", []),
        "created_at": datetime.utcnow()
    }
    
    history_entry = CompareHistory(**history_data)
    db.add(history_entry)
    await db.commit()
    await db.refresh(history_entry) # get ID
    
    print(f"✅ Saved compare history: {history_entry.id}")
    return str(history_entry.id)

async def get_user_compare_history(db: AsyncSession, user_id: str) -> List[CompareHistory]:
    """Fetch user's comparison history"""
    result = await db.execute(
        select(CompareHistory)
        .where(CompareHistory.user_id == user_id)
        .order_by(desc(CompareHistory.created_at))
    )
    return result.scalars().all()

async def check_duplicate_ingestion(db: AsyncSession, investor: str, version: str, user_id: str) -> bool:
    """Check if an ingestion with the same investor and version already exists for the user."""
    result = await db.execute(
        select(IngestHistory).where(
            IngestHistory.user_id == user_id,
            IngestHistory.investor == investor,
            IngestHistory.version == version
        )
    )
    return result.scalars().first() is not None

async def delete_ingest_history(db: AsyncSession, history_id: str, user_id: str) -> bool:
    """Delete an ingestion history record."""
    result = await db.execute(
        select(IngestHistory).where(IngestHistory.id == history_id, IngestHistory.user_id == user_id)
    )
    record = result.scalars().first()
    if record:
        await db.delete(record)
        await db.commit()
        return True
    return False

async def delete_compare_history(db: AsyncSession, history_id: str, user_id: str) -> bool:
    """Delete a comparison history record."""
    result = await db.execute(
        select(CompareHistory).where(CompareHistory.id == history_id, CompareHistory.user_id == user_id)
    )
    record = result.scalars().first()
    if record:
        await db.delete(record)
        await db.commit()
        return True
    return False

async def delete_all_ingest_history(db: AsyncSession, user_id: str) -> int:
    """Delete all ingest history records for a user."""
    # This might be simpler with delete().where()
    # But to return count, we execute delete
    stmt = delete(IngestHistory).where(IngestHistory.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount

async def delete_all_compare_history(db: AsyncSession, user_id: str) -> int:
    """Delete all comparison history records for a user."""
    stmt = delete(CompareHistory).where(CompareHistory.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount

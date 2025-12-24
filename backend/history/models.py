# backend/history/models.py

from database import db_manager
from typing import List, Dict
from datetime import datetime
from bson import ObjectId

async def _ensure_db():
    if db_manager.client is None:
        await db_manager.connect()

async def save_ingest_history(data: dict) -> str:
    """Save ingest job to history"""
    await _ensure_db()
    
    history_data = {
        "user_id": data["user_id"],
        "username": data.get("username", "Unknown"),
        "investor": data["investor"],
        "version": data["version"],
        "uploaded_file": data["uploaded_file"],
        "extracted_file": data["extracted_file"],
        "preview_data": data.get("preview_data", []),
        "effective_date": data.get("effective_date"),
        "expiry_date": data.get("expiry_date"),
        "gridfs_file_id": data.get("gridfs_file_id"),  # ✅ UPDATED: Store GridFS file ID
        "created_at": datetime.utcnow()
    }
    
    result = await db_manager.ingest_history.insert_one(history_data)
    print(f"✅ Saved ingest history: {result.inserted_id}")
    return str(result.inserted_id)

async def get_user_ingest_history(user_id: str) -> List[Dict]:
    """Fetch user's ingest history sorted by most recent first"""
    await _ensure_db()
        
    cursor = db_manager.ingest_history.find({"user_id": user_id}).sort("created_at", -1)
    history = []
    async for doc in cursor:
        history.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "username": doc.get("username", "Unknown"),
            "investor": doc.get("investor", ""),
            "version": doc.get("version", ""),
            "uploadedFile": doc.get("uploaded_file", ""),
            "extractedFile": doc.get("extracted_file", ""),
            "preview_data": doc.get("preview_data", []),
            "effective_date": doc.get("effective_date"),
            "expiry_date": doc.get("expiry_date"),
            "gridfs_file_id": doc.get("gridfs_file_id"),  # ✅ UPDATED: Return GridFS file ID
            "page_range": doc.get("page_range"),
            "guideline_type": doc.get("guideline_type"),
            "program_type": doc.get("program_type"),
            "created_at": doc["created_at"]
        })
    return history

async def save_compare_history(data: dict) -> str:
    """Save comparison job to history"""
    await _ensure_db()

    history_data = {
        "user_id": data["user_id"],
        "username": data.get("username", "Unknown"),
        "uploaded_file1": data["uploaded_file1"],
        "uploaded_file2": data["uploaded_file2"],
        "extracted_file": data["extracted_file"],
        "preview_data": data.get("preview_data", []),
        "created_at": datetime.utcnow()
    }
    
    result = await db_manager.compare_history.insert_one(history_data)
    print(f"✅ Saved compare history: {result.inserted_id}")
    return str(result.inserted_id)

async def get_user_compare_history(user_id: str) -> List[Dict]:
    """Fetch user's comparison history"""
    await _ensure_db()
        
    cursor = db_manager.compare_history.find({"user_id": user_id}).sort("created_at", -1)
    history = []
    async for doc in cursor:
        history.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "username": doc.get("username", "Unknown"),
            "uploadedFile1": doc.get("uploaded_file1", ""),
            "uploadedFile2": doc.get("uploaded_file2", ""),
            "extractedFile": doc.get("extracted_file", ""),
            "preview_data": doc.get("preview_data", []),
            "created_at": doc["created_at"]
        })
    return history

async def check_duplicate_ingestion(investor: str, version: str, user_id: str) -> bool:
    """Check if an ingestion with the same investor and version already exists for the user."""
    await _ensure_db()
        
    existing = await db_manager.ingest_history.find_one({
        "user_id": user_id,
        "investor": investor,
        "version": version
    })
    return existing is not None

async def delete_ingest_history(history_id: str, user_id: str) -> bool:
    """Delete an ingestion history record."""
    await _ensure_db()
        
    result = await db_manager.ingest_history.delete_one({
        "_id": ObjectId(history_id),
        "user_id": user_id
    })
    return result.deleted_count > 0

async def delete_compare_history(history_id: str, user_id: str) -> bool:
    """Delete a comparison history record."""
    await _ensure_db()
        
    result = await db_manager.compare_history.delete_one({
        "_id": ObjectId(history_id),
        "user_id": user_id
    })
    return result.deleted_count > 0

async def delete_all_ingest_history(user_id: str) -> int:
    """Delete all ingest history records for a user."""
    await _ensure_db()
    
    # Optional: Delete associated GridFS files if needed
    # This example only deletes the history records
    
    result = await db_manager.ingest_history.delete_many({
        "user_id": user_id
    })
    return result.deleted_count

async def delete_all_compare_history(user_id: str) -> int:
    """Delete all comparison history records for a user."""
    await _ensure_db()
        
    result = await db_manager.compare_history.delete_many({
        "user_id": user_id
    })
    return result.deleted_count

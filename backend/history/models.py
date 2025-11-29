# backend/history/models.py

import database
from typing import List, Dict
from datetime import datetime
from bson import ObjectId

async def save_ingest_history(data: dict) -> str:
    """Save ingest job to history"""
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
    
    if database.ingest_history_collection is None:
        raise ConnectionError("Database not initialized")
        
    result = await database.ingest_history_collection.insert_one(history_data)
    print(f"✅ Saved ingest history: {result.inserted_id}")
    return str(result.inserted_id)

async def get_user_ingest_history(user_id: str) -> List[Dict]:
    """Fetch user's ingest history sorted by most recent first"""
    if database.ingest_history_collection is None:
        raise ConnectionError("Database not initialized")
        
    cursor = database.ingest_history_collection.find({"user_id": user_id}).sort("created_at", -1)
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
            "created_at": doc["created_at"]
        })
    return history

async def save_compare_history(data: dict) -> str:
    """Save comparison job to history"""
    history_data = {
        "user_id": data["user_id"],
        "username": data.get("username", "Unknown"),
        "file1": data["file1"],
        "file2": data["file2"],
        "comparison_file": data["comparison_file"],
        "preview_data": data.get("preview_data", []),
        "created_at": datetime.utcnow()
    }
    
    if database.compare_history_collection is None:
        raise ConnectionError("Database not initialized")
        
    result = await database.compare_history_collection.insert_one(history_data)
    print(f"✅ Saved compare history: {result.inserted_id}")
    return str(result.inserted_id)

async def get_user_compare_history(user_id: str) -> List[Dict]:
    """Fetch user's comparison history"""
    if database.compare_history_collection is None:
        raise ConnectionError("Database not initialized")
        
    cursor = database.compare_history_collection.find({"user_id": user_id}).sort("created_at", -1)
    history = []
    async for doc in cursor:
        history.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "username": doc.get("username", "Unknown"),
            "file1": doc.get("file1", ""),
            "file2": doc.get("file2", ""),
            "comparisonFile": doc.get("comparison_file", ""),
            "preview_data": doc.get("preview_data", []),
            "created_at": doc["created_at"]
        })
    return history

async def check_duplicate_ingestion(investor: str, version: str, user_id: str) -> bool:
    """Check if an ingestion with the same investor and version already exists for the user."""
    if database.ingest_history_collection is None:
        return False
        
    existing = await database.ingest_history_collection.find_one({
        "user_id": user_id,
        "investor": investor,
        "version": version
    })
    return existing is not None

async def delete_ingest_history(history_id: str, user_id: str) -> bool:
    """Delete an ingestion history record."""
    if database.ingest_history_collection is None:
        raise ConnectionError("Database not initialized")
        
    result = await database.ingest_history_collection.delete_one({
        "_id": ObjectId(history_id),
        "user_id": user_id
    })
    return result.deleted_count > 0

async def delete_compare_history(history_id: str, user_id: str) -> bool:
    """Delete a comparison history record."""
    if database.compare_history_collection is None:
        raise ConnectionError("Database not initialized")
        
    result = await database.compare_history_collection.delete_one({
        "_id": ObjectId(history_id),
        "user_id": user_id
    })
    return result.deleted_count > 0

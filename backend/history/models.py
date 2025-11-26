# backend/history/models.py

from database import ingest_history_collection, compare_history_collection
from datetime import datetime
from bson import ObjectId
from typing import List, Dict


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
        "file_path": data.get("file_path"),  # ✅ NEW: Store file path
        "created_at": datetime.utcnow()
    }
    result = await ingest_history_collection.insert_one(history_data)
    print(f"✅ Saved ingest history: {result.inserted_id}")
    return str(result.inserted_id)


async def get_user_ingest_history(user_id: str) -> List[Dict]:
    """Fetch user's ingest history sorted by most recent first"""
    cursor = ingest_history_collection.find({"user_id": user_id}).sort("created_at", -1)
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
            "file_path": doc.get("file_path"),  # ✅ NEW: Return file path
            "created_at": doc["created_at"]
        })
    return history


async def delete_ingest_history(record_id: str, user_id: str) -> bool:
    """Delete ingest history record (user can only delete their own)"""
    try:
        result = await ingest_history_collection.delete_one({
            "_id": ObjectId(record_id),
            "user_id": user_id
        })
        return result.deleted_count > 0
    except Exception as e:
        print(f"❌ Error deleting history: {e}")
        return False


# ✅ NEW: Compare history functions
async def save_compare_history(data: dict) -> str:
    """Save compare job to history"""
    history_data = {
        "user_id": data["user_id"],
        "username": data.get("username", "Unknown"),
        "uploaded_file1": data["uploaded_file1"],
        "uploaded_file2": data["uploaded_file2"],
        "extracted_file": data["extracted_file"],
        "preview_data": data.get("preview_data", []),
        "created_at": datetime.utcnow()
    }
    result = await compare_history_collection.insert_one(history_data)
    print(f"✅ Saved compare history: {result.inserted_id}")
    return str(result.inserted_id)


async def get_user_compare_history(user_id: str) -> List[Dict]:
    """Fetch user's compare history sorted by most recent first"""
    cursor = compare_history_collection.find({"user_id": user_id}).sort("created_at", -1)
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


async def delete_compare_history(record_id: str, user_id: str) -> bool:
    """Delete compare history record (user can only delete their own)"""
    try:
        result = await compare_history_collection.delete_one({
            "_id": ObjectId(record_id),
            "user_id": user_id
        })
        return result.deleted_count > 0
    except Exception as e:
        print(f"❌ Error deleting compare history: {e}")
        return False


async def check_duplicate_ingestion(investor: str, version: str, user_id: str) -> bool:
    """Check if an ingestion with the same investor and version already exists for the user"""
    count = await ingest_history_collection.count_documents({
        "user_id": user_id,
        "investor": investor,
        "version": version
    })
    return count > 0

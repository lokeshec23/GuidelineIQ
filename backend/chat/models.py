# backend/chat/models.py

import database
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Dict, Optional


async def save_chat_message(session_id: str, role: str, content: str) -> str:
    """
    Save a chat message to the session history.
    """
    if database.chat_sessions_collection is None:
        raise ConnectionError("Database not initialized")
        
    message_data = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    result = await database.chat_sessions_collection.insert_one(message_data)
    return str(result.inserted_id)


async def get_chat_history(session_id: str, limit: int = 50) -> List[Dict]:
    """
    Retrieve chat history for a session.
    """
    if database.chat_sessions_collection is None:
        raise ConnectionError("Database not initialized")
        
    cursor = database.chat_sessions_collection.find(
        {"session_id": session_id}
    ).sort("timestamp", 1).limit(limit)
    
    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"],
            "content": doc["content"],
            "timestamp": doc["timestamp"]
        })
    
    return messages


async def cache_gemini_file_uri(gridfs_file_id: str, gemini_uri: str, gemini_name: str, ttl_hours: int = 48) -> str:
    """
    Cache a Gemini file URI to avoid re-uploading.
    """
    if database.gemini_file_cache_collection is None:
        raise ConnectionError("Database not initialized")
        
    expiry_time = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    cache_data = {
        "gridfs_file_id": gridfs_file_id,
        "gemini_uri": gemini_uri,
        "gemini_name": gemini_name,
        "created_at": datetime.utcnow(),
        "expires_at": expiry_time
    }
    
    # Upsert to avoid duplicates
    result = await database.gemini_file_cache_collection.update_one(
        {"gridfs_file_id": gridfs_file_id},
        {"$set": cache_data},
        upsert=True
    )
    
    return str(result.upserted_id) if result.upserted_id else "updated"


async def get_cached_file_uri(gridfs_file_id: str) -> Optional[Dict]:
    """
    Get cached Gemini file URI if still valid.
    """
    if database.gemini_file_cache_collection is None:
        return None
        
    cache_entry = await database.gemini_file_cache_collection.find_one({
        "gridfs_file_id": gridfs_file_id,
        "expires_at": {"$gt": datetime.utcnow()}  # Not expired
    })
    
    if cache_entry:
        return {
            "gemini_uri": cache_entry["gemini_uri"],
            "gemini_name": cache_entry["gemini_name"],
            "created_at": cache_entry["created_at"],
            "expires_at": cache_entry["expires_at"]
        }
    
    return None


async def clear_expired_cache():
    """Remove expired cache entries."""
    if database.gemini_file_cache_collection is None:
        return 0
        
    result = await database.gemini_file_cache_collection.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    print(f"🧹 Cleared {result.deleted_count} expired Gemini file cache entries")
    return result.deleted_count

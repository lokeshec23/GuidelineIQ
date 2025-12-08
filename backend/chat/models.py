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


# ==================== CONVERSATION MANAGEMENT ====================

async def create_conversation(session_id: str, title: Optional[str] = None) -> str:
    """
    Create a new chat conversation.
    
    Args:
        session_id: The ingestion/comparison session ID
        title: Optional conversation title (auto-generated if None)
    
    Returns:
        The conversation ID (as string)
    """
    if database.chat_conversations_collection is None:
        raise ConnectionError("Database not initialized")
    
    now = datetime.utcnow()
    conversation_data = {
        "session_id": session_id,
        "title": title or "New Conversation",
        "created_at": now,
        "updated_at": now,
        "last_message": "",
        "message_count": 0
    }
    
    result = await database.chat_conversations_collection.insert_one(conversation_data)
    return str(result.inserted_id)


async def get_conversations(session_id: str) -> List[Dict]:
    """
    Get all conversations for a session, sorted by most recent.
    
    Args:
        session_id: The ingestion/comparison session ID
    
    Returns:
        List of conversation objects with metadata
    """
    if database.chat_conversations_collection is None:
        raise ConnectionError("Database not initialized")
    
    cursor = database.chat_conversations_collection.find(
        {"session_id": session_id}
    ).sort("updated_at", -1)  # Most recent first
    
    conversations = []
    async for doc in cursor:
        conversations.append({
            "id": str(doc["_id"]),
            "title": doc["title"],
            "created_at": doc["created_at"],
            "updated_at": doc["updated_at"],
            "last_message": doc.get("last_message", ""),
            "message_count": doc.get("message_count", 0)
        })
    
    return conversations


async def update_conversation_metadata(
    conversation_id: str, 
    last_message: str, 
    timestamp: Optional[datetime] = None,
    title: Optional[str] = None
) -> bool:
    """
    Update conversation metadata.
    
    Args:
        conversation_id: The conversation ID
        last_message: The last message content (will be truncated for preview)
        timestamp: Optional timestamp (defaults to now)
        title: Optional new title
    
    Returns:
        True if updated successfully
    """
    if database.chat_conversations_collection is None:
        raise ConnectionError("Database not initialized")
    
    # Build $set fields
    set_fields = {
        "updated_at": timestamp or datetime.utcnow(),
        "last_message": last_message[:100]  # Truncate for preview
    }
    
    if title:
        set_fields["title"] = title
    
    # Build update query with separate operators
    update_query = {
        "$set": set_fields,
        "$inc": {"message_count": 1}
    }
    
    result = await database.chat_conversations_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        update_query
    )
    
    return result.modified_count > 0


async def delete_conversation(conversation_id: str) -> int:
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: The conversation ID
    
    Returns:
        Number of messages deleted
    """
    if database.chat_conversations_collection is None or database.chat_sessions_collection is None:
        raise ConnectionError("Database not initialized")
    
    # Delete all messages for this conversation
    messages_result = await database.chat_sessions_collection.delete_many({
        "conversation_id": conversation_id
    })
    
    # Delete the conversation itself
    await database.chat_conversations_collection.delete_one({
        "_id": ObjectId(conversation_id)
    })
    
    return messages_result.deleted_count


async def get_conversation_messages(conversation_id: str, limit: int = 100) -> List[Dict]:
    """
    Get all messages for a specific conversation.
    
    Args:
        conversation_id: The conversation ID
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of messages with role, content, and timestamp
    """
    if database.chat_sessions_collection is None:
        raise ConnectionError("Database not initialized")
    
    cursor = database.chat_sessions_collection.find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1).limit(limit)
    
    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"],
            "content": doc["content"],
            "timestamp": doc["timestamp"]
        })
    
    return messages


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """
    Generate a conversation title from the first message.
    
    Args:
        first_message: The first user message
        max_length: Maximum title length
    
    Returns:
        Truncated and cleaned title
    """
    # Remove extra whitespace and newlines
    title = " ".join(first_message.split())
    
    # Truncate if too long
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + "..."
    
    return title or "New Conversation"


async def save_chat_message_with_conversation(
    session_id: str, 
    conversation_id: str, 
    role: str, 
    content: str
) -> str:
    """
    Save a chat message to a specific conversation.
    
    Args:
        session_id: The ingestion/comparison session ID
        conversation_id: The conversation ID
        role: Message role ('user' or 'assistant')
        content: Message content
    
    Returns:
        The inserted message ID
    """
    if database.chat_sessions_collection is None:
        raise ConnectionError("Database not initialized")
    
    timestamp = datetime.utcnow()
    message_data = {
        "session_id": session_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": timestamp
    }
    
    result = await database.chat_sessions_collection.insert_one(message_data)
    
    # Update conversation metadata
    await update_conversation_metadata(conversation_id, content, timestamp)
    
    return str(result.inserted_id)

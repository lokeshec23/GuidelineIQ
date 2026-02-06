# backend/chat/models.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update, desc
from models.sql_models import ChatSession, ChatConversation, GeminiFileCache
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Remove _ensure_db as it is not needed with dependency injection

async def save_chat_message(db: AsyncSession, session_id: str, role: str, content: str) -> str:
    """
    Save a chat message to the session history.
    """
    history_entry = ChatSession(
        session_id=session_id,
        role=role,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.add(history_entry)
    await db.commit()
    await db.refresh(history_entry)
    return str(history_entry.id)


async def get_chat_history(db: AsyncSession, session_id: str, limit: int = 50) -> List[Dict]:
    """
    Retrieve chat history for a session.
    """
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.session_id == session_id)
        .order_by(ChatSession.timestamp.asc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return [{
        "role": msg.role,
        "content": msg.content,
        "timestamp": msg.timestamp or datetime.utcnow()
    } for msg in messages]


async def cache_gemini_file_uri(db: AsyncSession, gridfs_file_id: str, gemini_uri: str, gemini_name: str, ttl_hours: int = 48) -> str:
    """
    Cache a Gemini file URI to avoid re-uploading.
    """
    expiry_time = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    # Check if exists to update or insert (Upsert)
    result = await db.execute(select(GeminiFileCache).where(GeminiFileCache.gridfs_file_id == gridfs_file_id))
    cache_entry = result.scalars().first()
    
    if cache_entry:
        cache_entry.gemini_uri = gemini_uri
        cache_entry.gemini_name = gemini_name
        cache_entry.expires_at = expiry_time
        # created_at remains same
    else:
        cache_entry = GeminiFileCache(
            gridfs_file_id=gridfs_file_id,
            gemini_uri=gemini_uri,
            gemini_name=gemini_name,
            expires_at=expiry_time,
            created_at=datetime.utcnow()
        )
        db.add(cache_entry)
    
    await db.commit()
    await db.refresh(cache_entry)
    
    return str(cache_entry.id)


async def get_cached_file_uri(db: AsyncSession, gridfs_file_id: str) -> Optional[Dict]:
    """
    Get cached Gemini file URI if still valid.
    """
    result = await db.execute(
        select(GeminiFileCache).where(
            GeminiFileCache.gridfs_file_id == gridfs_file_id,
            GeminiFileCache.expires_at > datetime.utcnow()
        )
    )
    cache_entry = result.scalars().first()
    
    if cache_entry:
        return {
            "gemini_uri": cache_entry.gemini_uri,
            "gemini_name": cache_entry.gemini_name,
            "created_at": cache_entry.created_at,
            "expires_at": cache_entry.expires_at
        }
    
    return None


async def clear_expired_cache(db: AsyncSession):
    """Remove expired cache entries."""
    stmt = delete(GeminiFileCache).where(GeminiFileCache.expires_at < datetime.utcnow())
    result = await db.execute(stmt)
    await db.commit()
    print(f"🧹 Cleared {result.rowcount} expired Gemini file cache entries")
    return result.rowcount


# ==================== CONVERSATION MANAGEMENT ====================

async def create_conversation(db: AsyncSession, session_id: str, title: Optional[str] = None) -> str:
    """
    Create a new chat conversation.
    """
    now = datetime.utcnow()
    conversation = ChatConversation(
        session_id=session_id,
        title=title or "New Conversation",
        created_at=now,
        updated_at=now,
        last_message="",
        message_count=0
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return str(conversation.id)


async def get_conversations(db: AsyncSession, session_id: str) -> List[Dict]:
    """
    Get all conversations for a session, sorted by most recent.
    """
    result = await db.execute(
        select(ChatConversation)
        .where(ChatConversation.session_id == session_id)
        .order_by(desc(ChatConversation.updated_at))
    )
    conversations = result.scalars().all()
    
    return [{
        "id": str(c.id),
        "title": c.title,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "last_message": c.last_message or "",
        "message_count": c.message_count or 0
    } for c in conversations]


async def update_conversation_metadata(
    db: AsyncSession,
    conversation_id: str, 
    last_message: str, 
    timestamp: Optional[datetime] = None,
    title: Optional[str] = None
) -> bool:
    """ update conversation metadata """
    result = await db.execute(select(ChatConversation).where(ChatConversation.id == conversation_id))
    conversation = result.scalars().first()
    
    if not conversation:
        return False
        
    conversation.updated_at = timestamp or datetime.utcnow()
    conversation.last_message = last_message[:100]
    conversation.message_count += 1
    
    if title:
        conversation.title = title
        
    await db.commit()
    return True


async def delete_conversation(db: AsyncSession, conversation_id: str) -> int:
    """
    Delete a conversation and all its messages.
    """
    # Delete messages logic is handled by cascade="all, delete-orphan", 
    # but let's be explicit if needed or rely on cascade. 
    # The models define cascading relationship.
    # However, ChatSession has conversation_id FK.
    
    result = await db.execute(select(ChatConversation).where(ChatConversation.id == conversation_id))
    conversation = result.scalars().first()
    
    if conversation:
        await db.delete(conversation) # Cascade should delete messages
        await db.commit()
        return 1 # Simplified return, exact message count needs extra query if we rely on cascade
        
    return 0


async def get_conversation_messages(db: AsyncSession, conversation_id: str, limit: int = 100) -> List[Dict]:
    """
    Get all messages for a specific conversation.
    """
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.conversation_id == conversation_id)
        .order_by(ChatSession.timestamp.asc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return [{
        "role": msg.role,
        "content": msg.content,
        "timestamp": msg.timestamp
    } for msg in messages]


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """
    Generate a conversation title from the first message.
    """
    # Remove extra whitespace and newlines
    title = " ".join(first_message.split())
    
    # Truncate if too long
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + "..."
    
    return title or "New Conversation"


async def save_chat_message_with_conversation(
    db: AsyncSession,
    session_id: str, 
    conversation_id: str, 
    role: str, 
    content: str
) -> str:
    """
    Save a chat message to a specific conversation.
    """
    timestamp = datetime.utcnow()
    
    message_entry = ChatSession(
        session_id=session_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        timestamp=timestamp
    )
    
    db.add(message_entry)
    
    # Manually update conversation metadata instead of calling function to keep atomic transaction if needed,
    # but separating concerns is fine.
    # Using the helper fn:
    # We shouldn't commit in helper if we want single transaction, but existing code had distinct calls.
    # Let's commit message first.
    await db.commit()
    
    # Update conversation metadata
    await update_conversation_metadata(db, conversation_id, content, timestamp)
    
    return str(message_entry.id)

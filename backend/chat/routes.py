# backend/chat/routes.py

from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Optional
from bson import ObjectId
import os

from settings.models import get_user_settings
from auth.middleware import get_admin_user
import database
from chat.service import chat_with_gemini, upload_pdf_with_cache
from chat.models import (
    save_chat_message, get_chat_history,
    create_conversation, get_conversations, update_conversation_metadata,
    delete_conversation, get_conversation_messages, generate_conversation_title,
    save_chat_message_with_conversation
)
from utils.gridfs_helper import get_pdf_from_gridfs

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/session/{session_id}/message")
async def chat_with_session(
    session_id: str,
    message: str = Body(...),
    mode: str = Body(default="excel"),  # "pdf" or "excel"
    instructions: Optional[str] = Body(default=None),
    conversation_id: Optional[str] = Body(default=None),
):
    """
    Chat with a specific ingestion session.
    Supports two modes:
    - "pdf": Chat with the uploaded PDF using Google file search
    - "excel": Chat with the extracted Excel data
    
    Args:
        session_id: Ingestion session ID or history ID
        message: User's chat message
        mode: Chat mode ("pdf" or "excel")
        conversation_id: Optional conversation ID. If None, creates a new conversation
    
    Returns:
        Assistant's reply and updated chat history
    """
    # 1. Get API Key from Admin Settings
    if database.users_collection is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    admin_user = await database.users_collection.find_one({"role": "admin"})
    if not admin_user:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    settings = await get_user_settings(str(admin_user["_id"]))
    if not settings or not settings.get("gemini_api_key"):
        raise HTTPException(status_code=400, detail="Gemini API key not configured")
        
    api_key = settings["gemini_api_key"]
    
    # 2. Get session data from database
    record = None
    
    # Check if it's a valid ObjectId (history record)
    if ObjectId.is_valid(session_id):
        if database.ingest_history_collection is None or database.compare_history_collection is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Try ingest history first
        record = await database.ingest_history_collection.find_one({"_id": ObjectId(session_id)})
        
        # If not found in ingest history, try compare history
        if not record:
            record = await database.compare_history_collection.find_one({"_id": ObjectId(session_id)})
    
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 3. Handle conversation creation
    is_new_conversation = False
    if not conversation_id:
        # Create a new conversation
        conversation_id = await create_conversation(session_id, title="New Conversation")
        is_new_conversation = True
        print(f"✅ Created new conversation: {conversation_id}")
    
    # 4. Get chat history for this conversation
    history = await get_conversation_messages(conversation_id, limit=20)
    
    # 5. Prepare context based on mode
    file_uris = []
    text_context = ""
    
    if mode == "pdf":
        # PDF mode: Upload PDF to Gemini with caching
        gridfs_file_id = record.get("gridfs_file_id")
        
        if not gridfs_file_id:
            raise HTTPException(
                status_code=400, 
                detail="No PDF file associated with this session"
            )
        
        try:
            # Get PDF from GridFS
            pdf_content = await get_pdf_from_gridfs(gridfs_file_id)
            
            # Upload to Gemini with caching
            uploaded = await upload_pdf_with_cache(
                api_key=api_key,
                gridfs_file_id=gridfs_file_id,
                pdf_content=pdf_content,
                filename=record.get("uploaded_file", "document.pdf")
            )
            
            file_uris.append(uploaded["gemini_name"])
            
        except Exception as e:
            print(f"❌ Failed to upload PDF: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to prepare PDF: {str(e)}")
            
    elif mode == "excel":
        # Excel mode: Use preview data as text context
        preview_data = record.get("preview_data", [])
        
        if not preview_data:
            raise HTTPException(
                status_code=400,
                detail="No extracted data available for this session"
            )
        
        # Format preview data as structured text
        import json
        filename = record.get("uploaded_file", "Unknown File")
        investor = record.get("investor", "Unknown")
        version = record.get("version", "Unknown")
        
        text_context = f"""Mortgage Guidelines Data
Investor: {investor}
Version: {version}
Source File: {filename}

Extracted Guidelines:
{json.dumps(preview_data, indent=2)}
"""
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'pdf' or 'excel'")
    
    # 6. Call Gemini
    try:
        reply = chat_with_gemini(
            api_key=api_key,
            model_name="gemini-2.5-pro",  # Use latest model with file search
            message=message,
            history=history,
            file_uris=file_uris if mode == "pdf" else None,
            text_context=text_context if mode == "excel" else None,
            use_file_search=(mode == "pdf"),
            instructions=instructions
        )
        
        # 7. Save chat messages to conversation
        await save_chat_message_with_conversation(session_id, conversation_id, "user", message)
        await save_chat_message_with_conversation(session_id, conversation_id, "assistant", reply)
        
        # 8. If this is the first message, auto-generate title
        if is_new_conversation:
            title = generate_conversation_title(message)
            await update_conversation_metadata(conversation_id, message, title=title)
        
        # 9. Return reply with conversation ID
        updated_history = await get_conversation_messages(conversation_id, limit=20)
        
        return {
            "reply": reply,
            "history": updated_history,
            "mode": mode,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: Ingestion session ID or history ID
    
    Returns:
        List of chat messages
    """
    try:
        history = await get_chat_history(session_id, limit=50)
        return {"history": history}
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}/history")
async def clear_session_history(session_id: str):
    """
    Clear chat history for a session.
    
    Args:
        session_id: Ingestion session ID or history ID
    
    Returns:
        Success message
    """
    try:
        if database.chat_sessions_collection is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        result = await database.chat_sessions_collection.delete_many({"session_id": session_id})
        return {
            "message": f"Cleared {result.deleted_count} messages",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        print(f"❌ Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CONVERSATION MANAGEMENT ENDPOINTS ====================

@router.post("/session/{session_id}/conversations")
async def create_new_conversation(session_id: str, title: Optional[str] = Body(default=None, embed=True)):
    """
    Create a new conversation for a session.
    
    Args:
        session_id: Ingestion session ID or history ID
        title: Optional conversation title
    
    Returns:
        Conversation ID and metadata
    """
    try:
        conversation_id = await create_conversation(session_id, title)
        return {
            "conversation_id": conversation_id,
            "message": "Conversation created successfully"
        }
    except Exception as e:
        print(f"❌ Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/conversations")
async def list_conversations(session_id: str):
    """
    Get all conversations for a session.
    
    Args:
        session_id: Ingestion session ID or history ID
    
    Returns:
        List of conversations with metadata
    """
    try:
        conversations = await get_conversations(session_id)
        return {"conversations": conversations}
    except Exception as e:
        print(f"❌ Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{conversation_id}")
async def remove_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: The conversation ID
    
    Returns:
        Success message with count of deleted messages
    """
    try:
        deleted_count = await delete_conversation(conversation_id)
        return {
            "message": "Conversation deleted successfully",
            "deleted_messages": deleted_count
        }
    except Exception as e:
        print(f"❌ Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}/messages")
async def get_messages(conversation_id: str, limit: int = 100):
    """
    Get all messages for a conversation.
    
    Args:
        conversation_id: The conversation ID
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of messages with role, content, and timestamp
    """
    try:
        messages = await get_conversation_messages(conversation_id, limit)
        return {"messages": messages}
    except Exception as e:
        print(f"❌ Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


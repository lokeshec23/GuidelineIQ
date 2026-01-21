# backend/chat/routes.py

from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Optional
from bson import ObjectId
import os

from settings.models import get_user_settings
from auth.middleware import get_admin_user
import database
from chat.service import chat_with_gemini, chat_with_openai, upload_pdf_with_cache
from chat.rag_service import RAGService  # ✅ RAG Support
rag_service = RAGService()

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
        mode: Chat mode ("pdf", "excel", or "rag")
        conversation_id: Optional conversation ID. If None, creates a new conversation
    
    Returns:
        Assistant's reply and updated chat history
    """
    # 1. Get API Key from Admin Settings
    # 1. Get API Key from Admin Settings
    from database import db_manager
    if db_manager.users is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    admin_user = await db_manager.users.find_one({"role": "admin"})
    if not admin_user:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    settings = await get_user_settings(str(admin_user["_id"]))
    if not settings:
        raise HTTPException(status_code=400, detail="Settings not configured")
    
    # Check preferred provider
    provider = settings.get("default_model_provider", "openai")
    model_name = settings.get("default_model_name", "gpt-4o")
    
    api_key = None
    azure_params = {}

    if provider == "openai":
        api_key = settings.get("openai_api_key")
        if not api_key:
             raise HTTPException(status_code=400, detail="OpenAI API key not configured")
        
        # Check for Azure
        if settings.get("openai_endpoint"):
            azure_params = {
                "azure_endpoint": settings.get("openai_endpoint"),
                "azure_deployment": settings.get("openai_deployment"),
                "azure_embedding_deployment": settings.get("openai_embedding_deployment")
            }
            
    elif provider == "gemini":
        api_key = settings.get("gemini_api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
    else:
        # Fallback or error
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    # 2. Get session data from database
    record = None
    
    # Check if it's a valid ObjectId (history record)
    if ObjectId.is_valid(session_id):
        if db_manager.ingest_history is None or db_manager.compare_history is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Try ingest history first
        record = await db_manager.ingest_history.find_one({"_id": ObjectId(session_id)})
        
        # If not found in ingest history, try compare history
        if not record:
            record = await db_manager.compare_history.find_one({"_id": ObjectId(session_id)})
    
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
    
    # 5. Prepare context using RAG (for BOTH modes)
    gridfs_file_id = record.get("gridfs_file_id")
    investor = record.get("investor", "")
    version = record.get("version", "")
    
    if not gridfs_file_id:
         raise HTTPException(status_code=400, detail="No source file found for this session.")

    filter_metadata = {}
    
    if mode == "excel":
        # ✅ For Excel mode, filter by investor+version to find DSCR rules
        filter_metadata["type"] = "excel_rule"
        if investor:
            filter_metadata["investor"] = investor
        if version:
            filter_metadata["version"] = version
    elif mode == "pdf":
        # ✅ For PDF mode, search ALL PDF chunks for this investor/version
        filter_metadata["type"] = "pdf_chunk"
        if investor:
            filter_metadata["investor"] = investor
        if version:
            filter_metadata["version"] = version
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'pdf' or 'excel'")
 
    print(f"🔍 RAG Search ({mode}): '{message}' | Filter: {filter_metadata}")
    
    # Perform Vector Search
    results = await rag_service.search(
        query=message,
        provider=provider, # Dynamic provider
        api_key=api_key,
        n_results=20,  # ✅ INCREASED: Capture more context for broad queries
        filter_metadata=filter_metadata,
        **azure_params # Pass Azure params if any
    )
    
    text_context = ""
    file_uris = [] # Not used in RAG mode usually, unless we mix strategies
    
    if not results:
        text_context = "No relevant info found in the document index."
    else:
        context_parts = []
        for res in results:
            # res has 'text', 'metadata', 'distance'
            meta = res['metadata']
            source_type = meta.get('type', 'unknown')
            # ✅ Enhanced: Include filename in source attribution
            filename = meta.get('filename', 'Unknown')
            page_info = f"Page {meta.get('page')}" if meta.get('page') else "Unknown"
            
            if source_type == 'excel_rule':
                context_parts.append(f"--- [Rule | {filename} - {page_info}] ---\n{res['text']}\n")
            else:
                context_parts.append(f"--- [Text | {filename} - {page_info}] ---\n{res['text']}\n")
        
        text_context = "\n".join(context_parts)
        print(f"✅ RAG found {len(results)} items.")

    # 6. Call LLM (Gemini or OpenAI)
    try:
        reply = ""
        
        # ✅ Enhanced: Add strict summarization instructions
        enhanced_instructions = instructions or ""
        if text_context and text_context != "No relevant info found in the document index.":
            citation_instruction = """
            
STRICT INSTRUCTIONS:
1. Answer ONLY based on the provided context. Do NOT use your general knowledge.
2. If the context does not contain the answer, explicitly state: "I cannot find specific information about [topic] in the uploaded documents."

IMPORTANT: Provide direct, clear answers without referencing source documents or page numbers.
"""
            enhanced_instructions = (enhanced_instructions + citation_instruction).strip()
        
        if provider == "gemini":
            reply = chat_with_gemini(
                api_key=api_key,
                model_name=model_name,
                message=message,
                history=history,
                file_uris=[], 
                text_context=text_context,
                use_file_search=False,
                instructions=enhanced_instructions
            )
        elif provider == "openai":
            reply = chat_with_openai(
                api_key=api_key,
                model_name=model_name,
                message=message,
                history=history,
                text_context=text_context,
                instructions=enhanced_instructions,
                **azure_params
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
        from database import db_manager
        if db_manager.chat_sessions is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        result = await db_manager.chat_sessions.delete_many({"session_id": session_id})
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


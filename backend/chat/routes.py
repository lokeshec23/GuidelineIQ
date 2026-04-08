# backend/chat/routes.py

from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sql_database import get_db
from models.sql_models import User, IngestHistory, CompareHistory, ChatSession

from settings.models import get_user_settings
from auth.middleware import get_admin_user # Used as import, but we need to query admin user manually in route if not passed
# from database import db_manager # Removed
from chat.service import chat_with_openai
from rag_pipeline.retrieval.hybrid_retriever import HybridRetriever

from chat.models import (
    save_chat_message, get_chat_history,
    create_conversation, get_conversations, update_conversation_metadata,
    delete_conversation, get_conversation_messages, generate_conversation_title,
    save_chat_message_with_conversation
)
# from utils.gridfs_helper import get_pdf_from_gridfs # Removed
from utils.logger import setup_logger
import os
import json
from datetime import datetime

logger = setup_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/session/{session_id}/message")
async def chat_with_session(
    session_id: str,
    message: str = Body(...),
    mode: str = Body(default="excel"),  # "pdf" or "excel"
    instructions: Optional[str] = Body(default=None),
    conversation_id: Optional[str] = Body(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with a specific ingestion session.
    """
    # 1. Get API Key from Admin Settings
    # Find admin user
    result = await db.execute(select(User).where(User.role == "admin").limit(1))
    admin_user = result.scalars().first()
    
    # Fallback to is_admin flag if no explicit role="admin" found (handling both conventions)
    if not admin_user:
        result = await db.execute(select(User).where(User.is_admin == True).limit(1))
        admin_user = result.scalars().first()
        
    if not admin_user:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    settings = await get_user_settings(db, str(admin_user.id))
    if not settings:
        raise HTTPException(status_code=400, detail="Settings not configured")
    
    # Check preferred provider
    provider = settings.get("default_model_provider", "openai")
    model_name = settings.get("default_model_name", "gpt-4o")
    
    api_key = None
    azure_params = {}

    if provider == "openai":
        # Prefer DB-stored settings; fall back to .env if missing (same pattern as ingest/processor.py)
        api_key = (
            settings.get("openai_api_key")
            or os.getenv("AZURE_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured. Set it in Admin Settings or AZURE_OPENAI_API_KEY in .env")

        # Resolve endpoint and deployment with .env fallback
        endpoint = (
            settings.get("openai_endpoint")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        deployment = (
            settings.get("openai_deployment")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
        embedding_deployment = (
            settings.get("openai_embedding_deployment")
            or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        )

        if not all([endpoint, deployment]):
            missing = [k for k, v in {"endpoint": endpoint, "deployment": deployment}.items() if not v]
            raise HTTPException(
                status_code=400,
                detail=f"Azure OpenAI configuration incomplete. Missing: {missing}. Set in Admin Settings or .env"
            )

        azure_params = {
            "azure_endpoint": endpoint,
            "azure_deployment": deployment,
            "azure_embedding_deployment": embedding_deployment
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}. Only 'openai' (Azure OpenAI) is supported.")
    
    # 2. Get session data from database
    record = None
    
    # Try ingest history by ID
    result = await db.execute(select(IngestHistory).where(IngestHistory.id == session_id))
    record = result.scalars().first()
    
    # If not found, try compare history by ID
    if not record:
        result = await db.execute(select(CompareHistory).where(CompareHistory.id == session_id))
        record = result.scalars().first()
        
    # Fallback: Try looking up by 'session_id' field (UUID) if not found by primary key
    if not record:
        result = await db.execute(select(CompareHistory).where(CompareHistory.session_id == session_id))
        record = result.scalars().first()
        
        if not record:
             result = await db.execute(select(IngestHistory).where(IngestHistory.version == session_id)) # Was 'session_id' field in Mongodb? IngestHistory model has 'version', 'investor'. SQL model does NOT have 'session_id'. Except CompareHistory has it.
             # Wait, SQL IngestHistory model does NOT have session_id. MongoDB code had `find_one({"session_id": session_id})` fallback? 
             # Looking at old code logic: 
             # `record = await db_manager.ingest_history.find_one({"session_id": session_id})`
             # If mapping was lost, I should rely on ID.
             record = result.scalars().first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    # 3. Handle conversation creation
    is_new_conversation = False
    if not conversation_id:
        # Create a new conversation
        conversation_id = await create_conversation(db, session_id, title="New Conversation")
        is_new_conversation = True
        logger.info(f"Created new conversation: {conversation_id}")


    
    # 4. Get chat history for this conversation
    history = await get_conversation_messages(db, conversation_id, limit=20)
    
    # 5. Prepare context using RAG (for BOTH modes)
    # Access attributes safely
    gridfs_file_id = getattr(record, "gridfs_file_id", None)
    preview_data = getattr(record, "preview_data", None)
    investor = getattr(record, "investor", "")
    version = getattr(record, "version", "")
    extracted_file = getattr(record, "extracted_file", None)
    
    # Validation: strict for ingestion (needs file), loose for comparison (needs data)
    if not gridfs_file_id and not preview_data and not extracted_file:
         raise HTTPException(status_code=400, detail="No source file found for this session.")

    text_context = ""
    
    # STRATEGY 1: Comparison Session (Use formatted preview_data)
    # Comparison sessions don't have gridfs_file_id, but have preview_data
    if not gridfs_file_id and preview_data:
        logger.info(f"Using formatted preview_data for context ({len(preview_data)} items)")
        try:
            # Convert list of comparison results to a readable format for the LLM
            context_parts = []
            for item in preview_data[:100]: # Safety limit
                param = item.get("dscr_parameters") or item.get("parameter") or "Unknown"
                g1 = item.get("guideline_1") or item.get("guideline_1_value") or "N/A"
                g2 = item.get("guideline_2") or item.get("guideline_2_value") or "N/A"
                notes = item.get("comparison_notes") or ""
                
                context_parts.append(f"Parameter: {param}\nGuideline 1: {g1}\nGuideline 2: {g2}\nNotes: {notes}\n")
            
            text_context = "-- COMPARISON RESULTS --\n" + "\n".join(context_parts)
        except Exception as e:
             logger.error(f"Failed to format preview_data: {e}")
             text_context = str(preview_data)[:10000] # Fallback to truncated string

    # STRATEGY 2: Ingestion Session (Use RAG)
    elif gridfs_file_id:
        filter_metadata = {}
        
        # Base filters
        if investor:
            filter_metadata["lender"] = investor
        if version:
            filter_metadata["version"] = version

        # Mode-specific filtering
        if mode == "excel":
            # CRITICAL: Only search extracted rules in Excel mode
            filter_metadata["type"] = "excel_rule"
            logger.info("Excel Mode: Filtering for 'type: excel_rule'")
        else:
            # In PDF mode, we want the document chunks. 
            # We don't have a negative filter in current QdrantManager, 
            # but usually 'type' is only set for excel_rules.
            logger.info("PDF Mode: Searching document chunks")
     
        logger.info(f"RAG Search ({mode}): '{message}' | Filter: {filter_metadata}")
        
        # Initialize HybridRetriever
        hybrid_retriever = HybridRetriever()

        # Load context for BM25 (This is the bottleneck - adding filters helps)
        hybrid_retriever.load_context(filter_metadata)

        # Perform Search
        results = await hybrid_retriever.search(
            query=message,
            filter_conditions=filter_metadata,
            top_k=50  # Balanced for context quality and speed
        )
        
        if not results:
            logger.warning(f"RAG search returned 0 results for query: '{message}'")
            reply = "Result not found in the documents."
            await save_chat_message_with_conversation(db, session_id, conversation_id, "user", message)
            await save_chat_message_with_conversation(db, session_id, conversation_id, "assistant", reply)

            # Return immediate response
            updated_history = await get_conversation_messages(db, conversation_id, limit=20)
            return {
                "reply": reply,
                "history": updated_history,
                "mode": mode,
                "conversation_id": conversation_id
            }

        context_parts = []
        for res in results:
            chunk = res.chunk
            meta = chunk.metadata
            filename = meta.get('filename', 'Unknown')
            page_info = f"Page {chunk.page_start}" if chunk.page_start else "Source: Extracted Rules"
            
            context_parts.append(f"--- [{filename} - {page_info}] ---\n{chunk.text}\n")
        
        text_context = "\n".join(context_parts)
        logger.info(f"RAG found {len(results)} items.")


    # 6. Call Azure OpenAI
    try:
        reply = ""
        
        # ✅ Enhanced: Add strict summarization instructions
        enhanced_instructions = instructions or ""

        # Define mode-specific context instructions
        mode_instruction = ""
        if mode == "excel":
            mode_instruction = (
                "You are a senior US Non-QM mortgage underwriter analyzing structured guideline data extracted into Excel format. "
                "You must answer strictly based on the provided guideline content and never hallucinate missing values. "
                "When numeric limits such as LTV, FICO, DSCR, loan amount, reserves, or property type restrictions are present, "
                "you must cross-check all relevant conditions before answering. "
                "If a user presents a scenario (e.g., specific FICO, LTV, DSCR, property type, loan purpose), you must perform "
                "step-by-step eligibility reasoning by comparing each parameter against the guideline limits and explicitly state "
                "Pass/Fail for each condition before giving a final eligibility decision. "
                "If requested LTV exceeds maximum allowed LTV, clearly state “Not Eligible – exceeds maximum LTV of X%.” "
                "If information is not found, state “Not found in provided guideline section” instead of assuming. "
                "Always check related overlays such as loan amount tiers, property type restrictions, cash-out differences, "
                "reserve requirements, and FICO impacts before concluding. "
                "Provide structured answers in this format when eligibility is asked: "
                "Eligibility: Yes/No. Reasoning: LTV check – ; FICO check – ; DSCR check – ; Loan amount check – ; Property type check – ; Reserve requirement – . "
                "Do not provide generic answers; only use extracted data. If multiple tiers exist, clearly differentiate them. "
                "Your role is to behave like an underwriting decision engine, not a search assistant."
            )
        elif not gridfs_file_id and preview_data:
            mode_instruction = "You are analyzing a COMPARISON between two mortgage guidelines. Explain the differences or details as requested based on the provided comparison summary."
        else:
             mode_instruction = "You are analyzing a mortgage guideline document. Answer strictly based on the provided text."

        if text_context and text_context != "No relevant info found in the document index.":
            citation_instruction = f"""
            
STRICT INSTRUCTIONS:
1. {mode_instruction}
2. Answer ONLY based on the provided context. Do NOT use your general knowledge.
3. If the context does not contain the answer, state: "Not found in provided guideline section".
4. If the query is broad, provide a logical summary using bullet points.
5. Provide direct answers without referencing page numbers or internal technical IDs.
"""
            enhanced_instructions = (enhanced_instructions + citation_instruction).strip()
        
        reply = chat_with_openai(
            api_key=api_key,
            model_name=model_name,
            message=message,
            history=history,
            text_context=text_context,
            instructions=enhanced_instructions,
            **azure_params
        )
        
        # 6.5 Generate Follow-up Suggestions if New Conversation
        suggestions = []
        try:
            suggestions_prompt = (
                "Based STRICTLY on the user's specific query and the assistant's direct answer, suggest 3 highly relevant follow-up "
                "questions. The questions MUST directly relate to the user's original intent and the provided answer, acting as natural next steps in the conversation. "
                "Do NOT suggest generic or unrelated guideline questions. "
                "Return ONLY a JSON array of 3 strings. Example: [\"Question 1?\", \"Question 2?\", \"Question 3?\"]"
            )
            
            # We can call the same chat service, just overriding the message and instructions to get the JSON
            suggestions_reply = chat_with_openai(
                api_key=api_key,
                model_name=model_name,
                message=suggestions_prompt,
                history=[], # Don't need history, we just need the context of current interaction
                text_context=f"User's query: {message}\nAssistant's answer: {reply}",
                instructions="You are an assistant that only outputs a valid JSON array of 3 concise follow-up questions strictly related to the user's query.",
                **azure_params
            )
            
            # Parse the JSON response
            # Sometimes LLMs wrap JSON in markdown blocks
            if "```json" in suggestions_reply:
                suggestions_reply = suggestions_reply.split("```json")[-1].split("```")[0].strip()
            elif "```" in suggestions_reply:
                suggestions_reply = suggestions_reply.split("```")[-1].split("```")[0].strip()
                
            parsed_suggestions = json.loads(suggestions_reply)
            if isinstance(parsed_suggestions, list) and len(parsed_suggestions) > 0:
                suggestions = [str(s) for s in parsed_suggestions][:3]
        except Exception as e:
            logger.error(f"Failed to generate follow-up suggestions: {e}")
            # Don't fail the main request if suggestions fail
            pass
        
        # 7. Save chat messages to conversation
        await save_chat_message_with_conversation(db, session_id, conversation_id, "user", message)
        await save_chat_message_with_conversation(db, session_id, conversation_id, "assistant", reply)
        
        # 8. If this is the first message, auto-generate title
        if is_new_conversation:
            title = generate_conversation_title(message)
            # Need to pass db to update_conversation_metadata? Yes.
            await update_conversation_metadata(db, conversation_id, message, title=title)
        
        # 9. Return reply with conversation ID
        updated_history = await get_conversation_messages(db, conversation_id, limit=20)
        
        response_data = {
            "reply": reply,
            "history": updated_history,
            "mode": mode,
            "conversation_id": conversation_id
        }
        
        if suggestions:
            response_data["suggestions"] = suggestions
            
        return response_data
        
    except Exception as e:
        logger.error(f"Chat Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get chat history for a session.
    """
    try:
        history = await get_chat_history(db, session_id, limit=50)
        return {"history": history}
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/session/{session_id}/history")
async def clear_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Clear chat history for a session.
    """
    try:
        stmt = delete(ChatSession).where(ChatSession.session_id == session_id)
        result = await db.execute(stmt)
        await db.commit()
        return {
            "message": f"Cleared {result.rowcount} messages",
            "deleted_count": result.rowcount
        }
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==================== CONVERSATION MANAGEMENT ENDPOINTS ====================

@router.post("/session/{session_id}/conversations")
async def create_new_conversation(
    session_id: str, 
    title: Optional[str] = Body(default=None, embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation for a session.
    """
    try:
        conversation_id = await create_conversation(db, session_id, title)
        return {
            "conversation_id": conversation_id,
            "message": "Conversation created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/session/{session_id}/conversations")
async def list_conversations(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get all conversations for a session.
    """
    try:
        conversations = await get_conversations(db, session_id)
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/conversation/{conversation_id}")
async def remove_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a conversation and all its messages.
    """
    try:
        deleted_count = await delete_conversation(db, conversation_id)
        return {
            "message": "Conversation deleted successfully",
            "deleted_messages": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/conversation/{conversation_id}/messages")
async def get_messages(conversation_id: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Get all messages for a conversation.
    """
    try:
        messages = await get_conversation_messages(db, conversation_id, limit)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))



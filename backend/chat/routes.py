from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Optional
from bson import ObjectId
import os

from settings.models import get_user_settings
from auth.middleware import get_admin_user
from database import ingest_history_collection
from chat.service import upload_file_to_gemini, chat_with_gemini

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/message")
async def chat_message(
    message: str = Body(...),
    history: List[Dict] = Body(default=[]),
    mode: str = Body(default="excel"),  # "pdf" or "excel"
    context_ids: List[str] = Body(default=[])
):
    """
    Handle chat messages with context from PDF or Excel data.
    """
    # 1. Get API Key from Admin Settings
    admin_user = await get_admin_user()
    if not admin_user:
        raise HTTPException(status_code=500, detail="Admin user not found")
    
    settings = await get_user_settings(str(admin_user["_id"]))
    if not settings or not settings.get("gemini_api_key"):
        raise HTTPException(status_code=400, detail="Gemini API key not configured")
        
    api_key = settings["gemini_api_key"]
    
    # 2. Prepare Context
    file_uris = []
    text_context = ""
    
    if context_ids:
        # Convert string IDs to ObjectIds
        obj_ids = [ObjectId(id) for id in context_ids if ObjectId.is_valid(id)]
        
        if obj_ids:
            # Fetch records
            cursor = ingest_history_collection.find({"_id": {"$in": obj_ids}})
            records = await cursor.to_list(length=len(obj_ids))
            
            if mode == "pdf":
                # Upload PDFs
                for record in records:
                    file_path = record.get("file_path")
                    if file_path and os.path.exists(file_path):
                        try:
                            # Upload to Gemini
                            # Note: In a production app, we should cache these URIs 
                            # and check if they are still valid to avoid re-uploading.
                            # For now, we upload every time or rely on the service to handle it.
                            # Since the service just calls upload_file, it will create a new file resource.
                            # TODO: Implement caching of file URIs in the database.
                            uploaded_file = upload_file_to_gemini(api_key, file_path)
                            file_uris.append(uploaded_file.name)
                        except Exception as e:
                            print(f"❌ Failed to upload PDF {file_path}: {e}")
                    else:
                        print(f"⚠️ PDF file not found for record {record.get('_id')}")
                        
            elif mode == "excel":
                # Prepare Text Context from Preview Data
                context_parts = []
                for record in records:
                    filename = record.get("uploaded_file", "Unknown File")
                    data = record.get("preview_data", [])
                    
                    context_parts.append(f"--- FILE: {filename} ---")
                    # Convert list of dicts to a string representation
                    # We can format it as JSON or a readable list
                    import json
                    data_str = json.dumps(data, indent=2)
                    context_parts.append(data_str)
                    
                text_context = "\n\n".join(context_parts)

    # 3. Call Gemini
    try:
        reply = chat_with_gemini(
            api_key=api_key,
            model_name="gemini-2.5-pro", # Use a capable model
            message=message,
            history=history,
            file_uris=file_uris,
            text_context=text_context
        )
        
        return {"reply": reply}
        
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

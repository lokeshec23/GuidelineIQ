import os
import tempfile
import google.generativeai as genai
from typing import List, Dict, Optional

def configure_gemini(api_key: str):
    """Configures the Gemini SDK with the provided API key."""
    genai.configure(api_key=api_key)

def upload_file_to_gemini(api_key: str, file_path: str, mime_type: str = "application/pdf"):
    """
    Uploads a file to Gemini using the File API.
    Returns the file object (which contains the URI and name).
    """
    configure_gemini(api_key)
    
    print(f"📤 Uploading file to Gemini: {file_path}")
    file = genai.upload_file(file_path, mime_type=mime_type)
    print(f"✅ File uploaded: {file.uri} (name: {file.name})")
    
    return file

def chat_with_gemini(
    api_key: str,
    model_name: str,
    message: str,
    history: List[Dict],
    file_uris: Optional[List[str]] = None,
    text_context: Optional[str] = None,
    use_file_search: bool = True
) -> str:
    """
    Sends a message to Gemini, optionally with file attachments or text context.
    
    Args:
        api_key: Gemini API key
        model_name: Model to use (e.g., 'gemini-2.0-flash-exp')
        message: User message
        history: Chat history as list of dicts with 'role' and 'content'
        file_uris: List of Gemini file names (e.g., ['files/xxx'])
        text_context: Text context for Excel mode
        use_file_search: Whether to enable file search tool
    
    Returns:
        Assistant's reply
    """
    configure_gemini(api_key)
    
    # ✅ Configure tools for file search if needed
    tools = None
    if use_file_search and file_uris:
        # Enable file search tool for better RAG
        tools = [{"file_search": {}}]
    
    # Initialize model with tools
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=tools if tools else None
    )
    
    # Prepare chat history for Gemini SDK
    gemini_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
        
    # Start chat session
    chat = model.start_chat(history=gemini_history)
    
    # Prepare current message parts
    parts = []
    
    # Add text context if provided (for Excel mode)
    if text_context:
        context_msg = f"""You are a helpful assistant analyzing mortgage guideline data. 
        
Here is the context data from Excel:

{text_context}

Please answer the following question based on this data:
"""
        parts.append({"text": context_msg})
        
    # Add user message
    parts.append({"text": message})
    
    # Add file references if provided (for PDF mode)
    if file_uris:
        for uri in file_uris:
            try:
                # Retrieve the file object using the file name
                file_ref = genai.get_file(uri)
                parts.append(file_ref)
                print(f"✅ Added file to context: {uri}")
            except Exception as e:
                print(f"⚠️ Failed to retrieve file {uri}: {e}")

    # Send message
    try:
        response = chat.send_message(parts)
        return response.text
    except Exception as e:
        print(f"❌ Chat error: {e}")
        raise


async def upload_pdf_with_cache(api_key: str, gridfs_file_id: str, pdf_content: bytes, filename: str):
    """
    Upload PDF to Gemini with caching support.
    
    Args:
        api_key: Gemini API key
        gridfs_file_id: GridFS file ID for caching
        pdf_content: PDF file content as bytes
        filename: Original filename
    
    Returns:
        Dict with gemini_uri and gemini_name
    """
    from chat.models import get_cached_file_uri, cache_gemini_file_uri
    
    # Check cache first
    cached = await get_cached_file_uri(gridfs_file_id)
    if cached:
        print(f"✅ Using cached Gemini file: {cached['gemini_name']}")
        return {
            "gemini_uri": cached["gemini_uri"],
            "gemini_name": cached["gemini_name"]
        }
    
    # Not cached, upload to Gemini
    # Create temporary file
    temp_path = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
        prefix="gemini_upload_"
    ).name
    
    try:
        with open(temp_path, "wb") as f:
            f.write(pdf_content)
        
        # Upload to Gemini
        uploaded_file = upload_file_to_gemini(api_key, temp_path, "application/pdf")
        
        # Cache the result
        await cache_gemini_file_uri(
            gridfs_file_id=gridfs_file_id,
            gemini_uri=uploaded_file.uri,
            gemini_name=uploaded_file.name,
            ttl_hours=48  # Gemini files typically last 48 hours
        )
        
        return {
            "gemini_uri": uploaded_file.uri,
            "gemini_name": uploaded_file.name
        }
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

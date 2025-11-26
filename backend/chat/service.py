import os
import google.generativeai as genai
from typing import List, Dict, Optional

def configure_gemini(api_key: str):
    """Configures the Gemini SDK with the provided API key."""
    genai.configure(api_key=api_key)

def upload_file_to_gemini(api_key: str, file_path: str, mime_type: str = "application/pdf"):
    """
    Uploads a file to Gemini using the File API.
    Returns the file object (which contains the URI).
    """
    configure_gemini(api_key)
    
    print(f"📤 Uploading file to Gemini: {file_path}")
    file = genai.upload_file(file_path, mime_type=mime_type)
    print(f"✅ File uploaded: {file.uri}")
    
    return file

def chat_with_gemini(
    api_key: str,
    model_name: str,
    message: str,
    history: List[Dict],
    file_uris: Optional[List[str]] = None,
    text_context: Optional[str] = None
) -> str:
    """
    Sends a message to Gemini, optionally with file attachments or text context.
    """
    configure_gemini(api_key)
    
    # Initialize model
    model = genai.GenerativeModel(model_name)
    
    # Prepare chat history for Gemini SDK
    # Gemini expects history as a list of Content objects or dicts with 'role' and 'parts'
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
        parts.append(f"CONTEXT DATA:\n{text_context}\n\nUSER QUESTION:")
        
    parts.append(message)
    
    # Add file references if provided (for PDF mode)
    if file_uris:
        for uri in file_uris:
            # We need to retrieve the file object or construct a part that references it
            # The SDK allows passing the file object directly or a Part object
            # For simplicity, we'll assume we can pass the file object if we had it, 
            # but here we only have URIs. 
            # Actually, genai.GenerativeModel.generate_content accepts file objects.
            # But start_chat might be trickier with files in the middle of history.
            # For the *current* message, we can attach files.
            
            # We need to fetch the file object using get_file to pass it to the model
            # Or we can just pass the URI string? No, SDK needs the file object or specific structure.
            # Let's try to get the file object first.
            try:
                # This is a bit inefficient to do every time, but safe for now.
                # In a real app, we might cache the file object or its representation.
                # However, genai.get_file(name) returns a File object.
                # The name is usually 'files/...' which is part of the URI or the name attribute.
                # If file_uri is the full URI, we might need to parse it or store the name instead.
                # Let's assume file_uris contains the 'name' (e.g. 'files/xxxx').
                
                # If we passed the full URI, we might need to extract the name.
                # But let's assume the caller passes the 'name' property of the uploaded file.
                file_ref = genai.get_file(uri)
                parts.append(file_ref)
            except Exception as e:
                print(f"⚠️ Failed to retrieve file {uri}: {e}")

    # Send message
    response = chat.send_message(parts)
    
    return response.text

# backend/chat/service.py

import os
from typing import List, Dict, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


def chat_with_openai(
    api_key: str,
    model_name: str,
    message: str,
    history: List[Dict],
    text_context: Optional[str] = None,
    instructions: Optional[str] = None,
    **kwargs
) -> str:
    """
    Sends a message to Azure OpenAI Chat Completion API.
    
    Args:
        api_key: OpenAI API key
        model_name: Model to use (e.g., 'gpt-4o')
        message: User message
        history: Chat history
        text_context: RAG context to include
        instructions: System instructions
        **kwargs: Additional arguments for Azure OpenAI (azure_endpoint, azure_deployment)
    
    Returns:
        Assistant's reply
    """
    from openai import OpenAI, AzureOpenAI
    
    client = None
    if kwargs.get("azure_endpoint"):
        client = AzureOpenAI(
            api_key=api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=kwargs.get("azure_endpoint"),
            azure_deployment=kwargs.get("azure_deployment")
        )
    else:
        client = OpenAI(api_key=api_key)

    # Build messages list
    messages = []
    
    # 1. System Prompt
    system_content = "You are a helpful assistant analyzing mortgage guideline data."
    if instructions:
        system_content += f"\n\nSTRICT INSTRUCTIONS:\n{instructions}"
        
    messages.append({"role": "system", "content": system_content})
    
    # 2. History
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # 3. Current Context & Message
    final_user_content = message
    if text_context:
        final_user_content = f"CONTEXT DATA:\n{text_context}\n\nUSER QUESTION:\n{message}"
        
    messages.append({"role": "user", "content": final_user_content})
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI Chat error: {e}")
        raise

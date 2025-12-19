# backend/utils/logger.py

import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class LogLevel(str, Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogOperation(str, Enum):
    """Common operation types for logging"""
    # Authentication
    USER_REGISTER = "user_register"
    USER_LOGIN = "user_login"
    USER_LOGIN_FAILED = "user_login_failed"
    USER_LOGOUT = "user_logout"
    TOKEN_REFRESH = "token_refresh"
    
    # Ingestion
    INGEST_START = "ingest_start"
    INGEST_COMPLETE = "ingest_complete"
    INGEST_FAILED = "ingest_failed"
    INGEST_DOWNLOAD = "ingest_download"
    
    # Comparison
    COMPARE_START = "compare_start"
    COMPARE_COMPLETE = "compare_complete"
    COMPARE_FAILED = "compare_failed"
    COMPARE_DOWNLOAD = "compare_download"
    
    # Settings
    SETTINGS_VIEW = "settings_view"
    SETTINGS_UPDATE = "settings_update"
    SETTINGS_DELETE = "settings_delete"
    
    # Prompts
    PROMPT_CREATE = "prompt_create"
    PROMPT_UPDATE = "prompt_update"
    PROMPT_DELETE = "prompt_delete"
    PROMPT_VIEW = "prompt_view"
    
    # Chat
    CHAT_SESSION_CREATE = "chat_session_create"
    CHAT_MESSAGE_SEND = "chat_message_send"
    CHAT_SESSION_DELETE = "chat_session_delete"
    
    # History
    HISTORY_VIEW = "history_view"
    HISTORY_DELETE = "history_delete"
    
    # System
    SYSTEM_ERROR = "system_error"
    API_REQUEST = "api_request"


async def log_activity(
    user_id: str,
    username: str,
    operation: str,
    level: str = LogLevel.INFO,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    stack_trace: Optional[str] = None,
    display_name: Optional[str] = None
) -> bool:
    """
    Log an activity to the database.
    
    Args:
        user_id: User ID performing the operation
        username: Username/email of the user
        operation: Operation type (use LogOperation enum values)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        details: Additional structured data about the operation
        status: Operation status (success, failed, partial)
        error_message: Error message if operation failed
        stack_trace: Stack trace for errors
        
    Returns:
        bool: True if log was saved successfully, False otherwise
    """
    try:
        import database
        
        if database.activity_logs_collection is None:
            print("⚠️ Activity logs collection not initialized")
            return False
        
        log_entry = {
            "user_id": user_id,
            "username": username,
            "display_name": display_name or username,  # Fall back to username if display_name not provided
            "operation": operation,
            "level": level,
            "status": status,
            "details": details or {},
            "error_message": error_message,
            "stack_trace": stack_trace,
            "timestamp": datetime.utcnow(),
        }
        
        await database.activity_logs_collection.insert_one(log_entry)
        
        # Broadcast to WebSocket clients
        try:
            from logs.routes import broadcast_log
            # Create a serializable version of the log entry
            broadcast_entry = {
                "id": str(log_entry.get("_id", "")),
                "user_id": user_id,
                "username": username,
                "display_name": display_name or username,
                "operation": operation,
                "level": level,
                "status": status,
                "details": details or {},
                "error_message": error_message,
                "timestamp": log_entry["timestamp"].isoformat() if log_entry.get("timestamp") else None
            }
            await broadcast_log(broadcast_entry)
        except Exception as broadcast_err:
            # Don't fail logging if broadcast fails
            print(f"Failed to broadcast log: {broadcast_err}")
        
        return True
        
    except Exception as e:
        # Logging should never break the application
        print(f"❌ Failed to save activity log: {e}")
        traceback.print_exc()
        return False


# Convenience functions for common operations

async def log_auth_register(user_id: str, username: str, email: str) -> bool:
    """Log user registration"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.USER_REGISTER,
        level=LogLevel.INFO,
        details={"email": email}
    )


async def log_auth_login(user_id: str, username: str, remember_me: bool = False) -> bool:
    """Log successful login"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.USER_LOGIN,
        level=LogLevel.INFO,
        details={"remember_me": remember_me}
    )


async def log_auth_login_failed(email: str, reason: str = "Invalid credentials") -> bool:
    """Log failed login attempt"""
    return await log_activity(
        user_id="unknown",
        username=email,
        operation=LogOperation.USER_LOGIN_FAILED,
        level=LogLevel.WARNING,
        status="failed",
        details={"reason": reason}
    )


async def log_auth_logout(user_id: str, username: str) -> bool:
    """Log user logout"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.USER_LOGOUT,
        level=LogLevel.INFO
    )


async def log_token_refresh(user_id: str, username: str) -> bool:
    """Log token refresh"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.TOKEN_REFRESH,
        level=LogLevel.DEBUG
    )


async def log_ingest_start(
    user_id: str,
    username: str,
    session_id: str,
    filename: str,
    investor: str,
    version: str,
    model_provider: str,
    model_name: str
) -> bool:
    """Log ingestion start"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.INGEST_START,
        level=LogLevel.INFO,
        details={
            "session_id": session_id,
            "filename": filename,
            "investor": investor,
            "version": version,
            "model_provider": model_provider,
            "model_name": model_name
        }
    )


async def log_ingest_complete(
    user_id: str,
    username: str,
    session_id: str,
    investor: str,
    version: str,
    total_chunks: int,
    failed_chunks: int,
    processing_time: Optional[float] = None
) -> bool:
    """Log ingestion completion"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.INGEST_COMPLETE,
        level=LogLevel.INFO,
        details={
            "session_id": session_id,
            "investor": investor,
            "version": version,
            "total_chunks": total_chunks,
            "failed_chunks": failed_chunks,
            "processing_time_seconds": processing_time
        }
    )


async def log_ingest_failed(
    user_id: str,
    username: str,
    session_id: str,
    error: str,
    stack_trace: Optional[str] = None
) -> bool:
    """Log ingestion failure"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.INGEST_FAILED,
        level=LogLevel.ERROR,
        status="failed",
        details={"session_id": session_id},
        error_message=error,
        stack_trace=stack_trace
    )


async def log_compare_start(
    user_id: str,
    username: str,
    session_id: str,
    file1_name: str,
    file2_name: str,
    model_provider: str,
    model_name: str
) -> bool:
    """Log comparison start"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.COMPARE_START,
        level=LogLevel.INFO,
        details={
            "session_id": session_id,
            "file1_name": file1_name,
            "file2_name": file2_name,
            "model_provider": model_provider,
            "model_name": model_name
        }
    )


async def log_compare_complete(
    user_id: str,
    username: str,
    session_id: str,
    processing_time: Optional[float] = None
) -> bool:
    """Log comparison completion"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.COMPARE_COMPLETE,
        level=LogLevel.INFO,
        details={
            "session_id": session_id,
            "processing_time_seconds": processing_time
        }
    )


async def log_compare_failed(
    user_id: str,
    username: str,
    session_id: str,
    error: str,
    stack_trace: Optional[str] = None
) -> bool:
    """Log comparison failure"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.COMPARE_FAILED,
        level=LogLevel.ERROR,
        status="failed",
        details={"session_id": session_id},
        error_message=error,
        stack_trace=stack_trace
    )


async def log_settings_update(
    user_id: str,
    username: str,
    updated_fields: list
) -> bool:
    """Log settings update"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=LogOperation.SETTINGS_UPDATE,
        level=LogLevel.INFO,
        details={"updated_fields": updated_fields}
    )


async def log_error(
    user_id: str,
    username: str,
    operation: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """Log an error with full context"""
    return await log_activity(
        user_id=user_id,
        username=username,
        operation=operation,
        level=LogLevel.ERROR,
        status="failed",
        details=context or {},
        error_message=str(error),
        stack_trace=traceback.format_exc()
    )

# backend/logs/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class LogEntry(BaseModel):
    """Schema for a single log entry"""
    id: str
    user_id: str
    username: str
    display_name: Optional[str] = None
    operation: str
    level: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    timestamp: datetime


class LogsResponse(BaseModel):
    """Schema for paginated logs response"""
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int


class LogFilter(BaseModel):
    """Schema for filtering logs"""
    operation: Optional[str] = None
    level: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class LogStats(BaseModel):
    """Schema for log statistics"""
    total_logs: int
    operations: List[Dict[str, Any]]
    levels: List[Dict[str, Any]]
    most_active_users: List[Dict[str, Any]]
    recent_errors_24h: int

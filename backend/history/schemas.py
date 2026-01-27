# backend/history/schemas.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class IngestHistoryItem(BaseModel):
    """Schema for ingest history item"""
    id: str
    user_id: str
    username: str
    investor: str
    version: str
    uploadedFile: str  # Match frontend naming
    extractedFile: str  # Match frontend naming
    created_at: datetime
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    preview_data: Optional[List[Dict[str, Any]]] = None  # Excel output data
    pdf_files: Optional[List[Dict[str, Any]]] = None  # List of PDF metadata: [{file_index, filename, gridfs_file_id}]



class CompareHistoryItem(BaseModel):
    """Schema for compare history item"""
    id: str
    user_id: str
    username: str
    uploadedFile1: str
    uploadedFile2: str
    extractedFile: str
    created_at: datetime
    preview_data: Optional[List[Dict[str, Any]]] = None  # Comparison output data


class DeleteResponse(BaseModel):
    """Response for delete operations"""
    message: str
    success: bool


# backend/history/schemas.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any, Union


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
    preview_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None  # Excel output data
    pdf_files: Optional[List[Dict[str, Any]]] = None  # List of PDF metadata: [{file_index, filename, gridfs_file_id}]
    guideline_type: Optional[str] = None
    program_type: Optional[str] = None



class CompareHistoryItem(BaseModel):
    """Schema for compare history item"""
    id: str
    user_id: str
    username: str
    investor: Optional[str] = "Unknown Investor"
    version: Optional[str] = "v1"
    uploadedFile1: str
    uploadedFile2: str
    extractedFile: str
    created_at: datetime
    preview_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None  # Comparison output data


class DeleteResponse(BaseModel):
    """Response for delete operations"""
    message: str
    success: bool

class IngestHistoryPaginatedResponse(BaseModel):
    items: List[IngestHistoryItem]
    total: int
    page: int
    pageSize: int

class CompareHistoryPaginatedResponse(BaseModel):
    items: List[CompareHistoryItem]
    total: int
    page: int
    pageSize: int


# backend/utils/gridfs_helper.py

import io
import database
from typing import Optional, Dict, Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

async def save_pdf_to_gridfs(file_content: bytes, filename: str, metadata: Optional[Dict] = None) -> str:
    """
    Save a PDF file to GridFS.
    """
    if database.db_manager.fs is None:
        raise ConnectionError("GridFS not initialized")
        
    try:
        file_metadata = metadata or {}
        file_metadata["content_type"] = "application/pdf"
        file_metadata["original_filename"] = filename
        
        file_id = await database.db_manager.fs.upload_from_stream(
            filename,
            io.BytesIO(file_content),
            metadata=file_metadata
        )
        
        print(f"✅ Saved PDF to GridFS: {filename} (ID: {file_id})")
        return str(file_id)
        
    except Exception as e:
        print(f"❌ Failed to save PDF to GridFS: {e}")
        raise

async def get_pdf_from_gridfs(file_id: str) -> bytes:
    """
    Retrieve a PDF file from GridFS by its ID.
    """
    if database.db_manager.fs is None:
        raise ConnectionError("GridFS not initialized")
        
    try:
        if not ObjectId.is_valid(file_id):
            raise ValueError(f"Invalid file ID: {file_id}")
            
        grid_out = await database.db_manager.fs.open_download_stream(ObjectId(file_id))
        content = await grid_out.read()
        return content
        
    except Exception as e:
        print(f"❌ Failed to retrieve PDF from GridFS: {e}")
        raise

async def get_pdf_metadata(file_id: str) -> Optional[Dict]:
    """
    Get metadata for a file in GridFS.
    """
    if database.db_manager.db is None:
        raise ConnectionError("Database not initialized")
        
    try:
        if not ObjectId.is_valid(file_id):
            return None
            
        file_doc = await database.db_manager.db.fs.files.find_one({"_id": ObjectId(file_id)})
        return file_doc
        
    except Exception as e:
        print(f"❌ Failed to get PDF metadata: {e}")
        return None

async def delete_pdf_from_gridfs(file_id: str) -> bool:
    """
    Delete a file from GridFS.
    """
    if database.db_manager.fs is None:
        raise ConnectionError("GridFS not initialized")
        
    try:
        if not ObjectId.is_valid(file_id):
            return False
            
        await database.db_manager.fs.delete(ObjectId(file_id))
        print(f"✅ Deleted PDF from GridFS: {file_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to delete PDF from GridFS: {e}")
        return False

async def file_exists_in_gridfs(file_id: str) -> bool:
    """
    Check if a file exists in GridFS.
    """
    if database.db_manager.db is None:
        return False
        
    try:
        if not ObjectId.is_valid(file_id):
            return False
            
        count = await database.db_manager.db.fs.files.count_documents({"_id": ObjectId(file_id)})
        return count > 0
        
    except Exception:
        return False

# backend/utils/gridfs_helper.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.sql_models import File
from typing import Optional, Dict
from datetime import datetime

async def save_pdf_to_gridfs(db: AsyncSession, file_content: bytes, filename: str, metadata: Optional[Dict] = None) -> str:
    """
    Save a PDF file to SQL Database (replacing GridFS).
    Returns the file ID (UUID).
    """
    # Create File record
    new_file = File(
        content=file_content,
        filename=filename,
        content_type="application/pdf",
        created_at=datetime.utcnow()
    )
    
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    
    print(f"✅ Saved PDF to SQL: {filename} (ID: {new_file.id})")
    return str(new_file.id)

async def get_pdf_from_gridfs(db: AsyncSession, file_id: str) -> bytes:
    """
    Retrieve a PDF file from SQL Database by its ID.
    """
    file_record = await db.get(File, file_id)
    
    if not file_record:
        raise ValueError(f"File not found: {file_id}")
        
    return file_record.content

async def get_pdf_metadata(db: AsyncSession, file_id: str) -> Optional[Dict]:
    """
    Get metadata for a file in SQL Database.
    """
    result = await db.execute(select(File).where(File.id == file_id))
    file_record = result.scalars().first()
    
    if not file_record:
        return None
        
    return {
        "_id": file_record.id,
        "filename": file_record.filename,
        "uploadDate": file_record.created_at,
        "contentType": file_record.content_type
    }

async def delete_pdf_from_gridfs(db: AsyncSession, file_id: str) -> bool:
    """
    Delete a file from SQL Database.
    """
    result = await db.execute(select(File).where(File.id == file_id))
    file_record = result.scalars().first()
    
    if file_record:
        await db.delete(file_record)
        await db.commit()
        return True
    
    return False

async def file_exists_in_gridfs(db: AsyncSession, file_id: str) -> bool:
    """
    Check if a file exists in SQL Database.
    """
    result = await db.execute(select(File).where(File.id == file_id))
    file_record = result.scalars().first()
    return file_record is not None

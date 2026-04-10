from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sql_database import get_db
from models.sql_models import GuidelineType, DSCRParameter
from auth.middleware import require_admin
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

router = APIRouter(prefix="/guideline-types", tags=["Guideline Types"])

# --- Schemas ---
class GuidelineTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = None

class GuidelineTypeCreate(GuidelineTypeBase):
    pass

class GuidelineTypeUpdate(GuidelineTypeBase):
    pass

class GuidelineTypeResponse(GuidelineTypeBase):
    id: str
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]
    
    class Config:
        from_attributes = True

class GuidelineTypePaginatedResponse(BaseModel):
    items: List[GuidelineTypeResponse]
    total: int
    page: int
    pageSize: int

# --- Routes ---

from utils.pagination import paginate_query, PaginationParams

@router.get("", response_model=GuidelineTypePaginatedResponse)
async def list_guideline_types(
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    query = select(GuidelineType)
    return await paginate_query(db, query, GuidelineType, params, search_fields=["name", "description"])

@router.post("", response_model=GuidelineTypeResponse)
async def create_guideline_type(
    g_type: GuidelineTypeCreate, 
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    # Check for existing name
    existing = await db.execute(select(GuidelineType).where(GuidelineType.name == g_type.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Guideline type with this name already exists")
        
    new_type = GuidelineType(
        name=g_type.name,
        description=g_type.description,
        color=g_type.color
    )
    db.add(new_type)
    await db.commit()
    await db.refresh(new_type)
    return new_type

@router.put("/{type_id}", response_model=GuidelineTypeResponse)
async def update_guideline_type(
    type_id: str,
    g_type: GuidelineTypeUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    result = await db.execute(select(GuidelineType).where(GuidelineType.id == type_id))
    db_type = result.scalar_one_or_none()
    if not db_type:
        raise HTTPException(status_code=404, detail="Guideline type not found")
        
    # Check for name conflict
    existing = await db.execute(select(GuidelineType).where(GuidelineType.name == g_type.name))
    existing_scalar = existing.scalar_one_or_none()
    if existing_scalar and existing_scalar.id != type_id:
        raise HTTPException(status_code=400, detail="Guideline type with this name already exists")
    
    db_type.name = g_type.name
    db_type.description = g_type.description
    db_type.color = g_type.color
    await db.commit()
    await db.refresh(db_type)
    return db_type

@router.delete("/{type_id}")
async def delete_guideline_type(
    type_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    result = await db.execute(select(GuidelineType).where(GuidelineType.id == type_id))
    db_type = result.scalar_one_or_none()
    if not db_type:
        raise HTTPException(status_code=404, detail="Guideline type not found")
    
    # Check if in use
    # Note: guideline_type is a JSON column in DSCRParameter. 
    # Searching within JSON might require DB-specific functions, 
    # but for simplicity we can check if any parameter contains this name in its JSON array.
    # Since it's a small dataset, we can handle it or use a simple string search if needed.
    # For now, let's do a basic check.
    
    # Check if any parameters use this guideline type
    # (Doing this safely by checking name)
    params_check = await db.execute(select(DSCRParameter).where(DSCRParameter.guideline_type.contains(db_type.name)))
    if params_check.scalars().first():
        raise HTTPException(status_code=400, detail="Cannot delete guideline type because it is in use by one or more parameters")

    await db.delete(db_type)
    await db.commit()
    return {"message": "Guideline type deleted successfully"}

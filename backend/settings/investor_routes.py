from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sql_database import get_db
from models.sql_models import Investor
from auth.middleware import require_admin
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

router = APIRouter(prefix="/investors", tags=["Investors"])

# --- Schemas ---
class InvestorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class InvestorCreate(InvestorBase):
    pass

class InvestorUpdate(InvestorBase):
    pass

class InvestorResponse(InvestorBase):
    id: str
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]
    
    class Config:
        from_attributes = True

class InvestorPaginatedResponse(BaseModel):
    items: List[InvestorResponse]
    total: int
    page: int
    pageSize: int

# --- Routes ---

from utils.pagination import paginate_query, PaginationParams

@router.get("", response_model=InvestorPaginatedResponse)
async def list_investors(
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    query = select(Investor)
    return await paginate_query(db, query, Investor, params, search_fields=["name"])

@router.post("", response_model=InvestorResponse)
async def create_investor(
    investor: InvestorCreate, 
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    # Check for existing name
    existing = await db.execute(select(Investor).where(Investor.name == investor.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Investor with this name already exists")
        
    new_investor = Investor(name=investor.name)
    db.add(new_investor)
    await db.commit()
    await db.refresh(new_investor)
    return new_investor

@router.put("/{investor_id}", response_model=InvestorResponse)
async def update_investor(
    investor_id: str,
    investor: InvestorUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    result = await db.execute(select(Investor).where(Investor.id == investor_id))
    db_investor = result.scalar_one_or_none()
    if not db_investor:
        raise HTTPException(status_code=404, detail="Investor not found")
        
    # Check for name conflict
    existing = await db.execute(select(Investor).where(Investor.name == investor.name))
    existing_scalar = existing.scalar_one_or_none()
    if existing_scalar and existing_scalar.id != investor_id:
        raise HTTPException(status_code=400, detail="Investor with this name already exists")
    
    db_investor.name = investor.name
    await db.commit()
    await db.refresh(db_investor)
    return db_investor

@router.delete("/{investor_id}")
async def delete_investor(
    investor_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    result = await db.execute(select(Investor).where(Investor.id == investor_id))
    db_investor = result.scalar_one_or_none()
    if not db_investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    await db.delete(db_investor)
    await db.commit()
    return {"message": "Investor deleted successfully"}

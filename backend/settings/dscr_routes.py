from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sql_database import get_db
from models.sql_models import DSCRParameter
from settings.dscr_schemas import DSCRParameterCreate, DSCRParameterUpdate, DSCRParameterResponse, GUIDELINE_TYPE_OPTIONS
from auth.middleware import require_admin
from typing import List, Optional
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dscr-parameters", tags=["Parameters"])

@router.get("", response_model=List[DSCRParameterResponse])
async def list_parameters(
    investor_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 0,  # 0 = no limit (return all)
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()
    query = select(DSCRParameter)
    
    # Filter by specific investor_id, or None for general parameters
    if investor_id == "null" or investor_id is None:
        query = query.where(DSCRParameter.investor_id == None)
    elif investor_id != "all":
        query = query.where(DSCRParameter.investor_id == investor_id)
        
    query = query.order_by(DSCRParameter.category, DSCRParameter.parameter)
    
    if skip > 0:
        query = query.offset(skip)
    if limit > 0:
        query = query.limit(limit)

    db_start = time.time()
    result = await db.execute(query)
    parameters = result.scalars().all() or []
    db_end = time.time()
    
    logger.info(f"DB Query took {db_end - db_start:.4f}s for {len(parameters)} items")
    
    # Serialization happens after return
    logger.info(f"Total route logic took {time.time() - start_time:.4f}s")
    return parameters

@router.get("/guideline-types")
async def get_guideline_types():
    """Return available guideline type options for dropdowns."""
    return GUIDELINE_TYPE_OPTIONS

@router.post("", response_model=DSCRParameterResponse)
async def create_parameter(
    param: DSCRParameterCreate, 
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    new_param = DSCRParameter(**param.model_dump())
    db.add(new_param)
    await db.commit()
    await db.refresh(new_param)
    return new_param

@router.put("/{param_id}", response_model=DSCRParameterResponse)
async def update_parameter(
    param_id: str,
    param: DSCRParameterUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    result = await db.execute(select(DSCRParameter).where(DSCRParameter.id == param_id))
    db_param = result.scalar_one_or_none()
    if not db_param:
        raise HTTPException(status_code=404, detail="Parameter not found")
    
    update_data = param.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_param, key, value)
    
    await db.commit()
    await db.refresh(db_param)
    return db_param

@router.delete("/{param_id}")
async def delete_parameter(
    param_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    result = await db.execute(select(DSCRParameter).where(DSCRParameter.id == param_id))
    db_param = result.scalar_one_or_none()
    if not db_param:
        raise HTTPException(status_code=404, detail="Parameter not found")
    
    await db.delete(db_param)
    await db.commit()
    return {"message": "Parameter deleted successfully"}

from sqlalchemy import delete

@router.delete("")
async def delete_all_parameters(
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Delete all parameters from the database"""
    await db.execute(delete(DSCRParameter))
    await db.commit()
    return {"message": "All parameters deleted successfully"}

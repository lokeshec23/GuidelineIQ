from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sql_database import get_db
from models.sql_models import DSCRParameter, Investor
from settings.dscr_schemas import (
    DSCRParameterCreate, 
    DSCRParameterUpdate, 
    DSCRParameterResponse, 
    DSCRParameterPaginatedResponse,
    GUIDELINE_TYPE_OPTIONS,
    DSCRParameterBulkCreate,
    BatchImportRequest
)
from auth.middleware import require_admin
from utils.pagination import paginate_query, PaginationParams
from typing import List, Optional
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dscr-parameters", tags=["Parameters"])

@router.get("", response_model=DSCRParameterPaginatedResponse)
async def list_parameters(
    investor_id: Optional[str] = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()
    query = select(DSCRParameter)
    
    # Filter by specific investor_id, or None for general parameters
    if investor_id == "null" or investor_id is None:
        query = query.where(DSCRParameter.investor_id == None)
    elif investor_id != "all":
        query = query.where(DSCRParameter.investor_id == investor_id)
        
    result = await paginate_query(
        db, 
        query, 
        DSCRParameter, 
        params, 
        search_fields=["parameter", "category", "subcategory"]
    )
    
    logger.info(f"Paginated list_parameters took {time.time() - start_time:.4f}s")
    return result

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

@router.post("/bulk", response_model=List[DSCRParameterResponse])
async def bulk_create_parameters(
    batch: DSCRParameterBulkCreate,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Create multiple parameters in a single transaction."""
    new_params = [DSCRParameter(**param.model_dump()) for param in batch.parameters]
    db.add_all(new_params)
    await db.commit()
    for p in new_params:
        await db.refresh(p)
    return new_params

@router.post("/import-from-general", response_model=List[DSCRParameterResponse])
async def import_from_general(
    request: BatchImportRequest,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Import selected general parameters to a specific investor."""
    # 1. Fetch general parameters
    result = await db.execute(
        select(DSCRParameter).where(DSCRParameter.id.in_(request.parameter_ids))
    )
    general_params = result.scalars().all()
    
    # 2. Clone them for the target investor
    new_params = []
    for p in general_params:
        new_param = DSCRParameter(
            parameter=p.parameter,
            category=p.category,
            subcategory=p.subcategory,
            ppe_field=p.ppe_field,
            guideline_type=p.guideline_type,
            investor_id=request.target_investor_id
        )
        new_params.append(new_param)
    
    db.add_all(new_params)
    await db.commit()
    for p in new_params:
        await db.refresh(p)
    
    return new_params

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

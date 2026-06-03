from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import List, Optional
import time
import io
import re
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete, cast, String
from sql_database import get_db
from models.sql_models import DSCRParameter, Investor, GuidelineType
from settings.dscr_schemas import (
    DSCRParameterCreate, 
    DSCRParameterUpdate, 
    DSCRParameterResponse, 
    DSCRParameterPaginatedResponse,
    GUIDELINE_TYPE_OPTIONS,
    DSCRParameterBulkCreate,
    BatchImportRequest
)
import json
from auth.middleware import require_admin
from utils.pagination import paginate_query, apply_query_filters, PaginationParams
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/dscr-parameters", tags=["Parameters"])

@router.get("/ids", response_model=List[str])
async def get_parameter_ids(
    investor_id: Optional[str] = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Return all parameter IDs matching the filters, skipping pagination."""
    query = select(DSCRParameter.id)
    
    if investor_id == "null" or investor_id is None:
        query = query.where(DSCRParameter.investor_id == None, DSCRParameter.is_active == True)
    elif investor_id != "all":
        query = query.where(DSCRParameter.investor_id == investor_id, DSCRParameter.is_active == True)
    else:
        query = query.where(DSCRParameter.is_active == True)
        
    query = apply_query_filters(query, DSCRParameter, params, search_fields=["parameter", "category", "subcategory"])
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("", response_model=DSCRParameterPaginatedResponse)
async def list_parameters(
    investor_id: Optional[str] = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()
    
    query = select(DSCRParameter)
    if investor_id == "null" or investor_id is None:
        query = query.where(DSCRParameter.investor_id == None, DSCRParameter.is_active == True)
    elif investor_id != "all":
        query = query.where(DSCRParameter.investor_id == investor_id, DSCRParameter.is_active == True)
    else:
        query = query.where(DSCRParameter.is_active == True)
    
    result = await paginate_query(
        db, 
        query, 
        DSCRParameter, 
        params, 
        search_fields=["parameter", "category", "subcategory"]
    )
    
    stats_query = select(DSCRParameter.guideline_type)
    if investor_id == "null" or investor_id is None:
        stats_query = stats_query.where(DSCRParameter.investor_id == None, DSCRParameter.is_active == True)
    elif investor_id != "all":
        stats_query = stats_query.where(DSCRParameter.investor_id == investor_id, DSCRParameter.is_active == True)
    else:
        stats_query = stats_query.where(DSCRParameter.is_active == True)
        
    stats_query = apply_query_filters(stats_query, DSCRParameter, params, search_fields=["parameter", "category", "subcategory"])

    stats_result = await db.execute(stats_query)
    all_types = stats_result.scalars().all()
    
    available_types = [t for t in GUIDELINE_TYPE_OPTIONS if t != "All"]
    breakdown = {t: 0 for t in available_types}
    
    for types_json in all_types:
        types = types_json
        if isinstance(types, str):
            try:
                types = json.loads(types)
            except:
                types = [types]
        
        if not types:
            types = ["All"]
            
        if "All" in types:
            for t in available_types:
                breakdown[t] += 1
        else:
            for t in types:
                if t in breakdown:
                    breakdown[t] += 1
    
    result["breakdown"] = breakdown
    
    logger.info(f"Paginated list_parameters with stats took {time.time() - start_time:.4f}s")
    return result

@router.get("/unique-values")
async def get_unique_values(
    field: str,
    investor_id: Optional[str] = None,
    guideline_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    if field not in ["category", "subcategory"]:
        raise HTTPException(status_code=400, detail="Invalid field")
    
    query = select(getattr(DSCRParameter, field)).distinct()
    
    if investor_id == "null" or investor_id is None:
        query = query.where(DSCRParameter.investor_id == None, DSCRParameter.is_active == True)
    elif investor_id != "all":
        query = query.where(DSCRParameter.investor_id == investor_id, DSCRParameter.is_active == True)
    else:
        query = query.where(DSCRParameter.is_active == True)
        
    if guideline_type:
        query = query.where(or_(
            cast(DSCRParameter.guideline_type, String).ilike(f"%{guideline_type}%"),
            cast(DSCRParameter.guideline_type, String).ilike("%All%")
        ))
        
    result = await db.execute(query)
    values = result.scalars().all()
    
    return sorted([v for v in values if v])

@router.get("/guideline-types")
async def get_guideline_types():
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
    # Fetch general parameters
    result = await db.execute(
        select(DSCRParameter).where(DSCRParameter.id.in_(request.parameter_ids))
    )
    general_params = result.scalars().all()
    
    # Check what already exists to avoid duplicates
    existing_result = await db.execute(
        select(DSCRParameter).where(DSCRParameter.investor_id == request.target_investor_id)
    )
    existing_params = existing_result.scalars().all()
    existing_keys = {(p.category, p.parameter) for p in existing_params}
    
    new_params = []
    for p in general_params:
        if (p.category, p.parameter) not in existing_keys:
            new_param = DSCRParameter(
                parameter=p.parameter,
                category=p.category,
                subcategory=p.subcategory,
                ppe_field=p.ppe_field,
                guideline_type=p.guideline_type,
                investor_id=request.target_investor_id,
                is_active=True
            )
            new_params.append(new_param)
    
    if new_params:
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

@router.delete("")
async def delete_all_parameters(
    investor_id: Optional[str] = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    query = delete(DSCRParameter)
    
    if investor_id == "null" or investor_id is None:
        query = query.where(DSCRParameter.investor_id == None)
    elif investor_id != "all":
        query = query.where(DSCRParameter.investor_id == investor_id)
        
    query = apply_query_filters(query, DSCRParameter, params, search_fields=["parameter", "category", "subcategory"])
    
    await db.execute(query)
    await db.commit()
    return {"message": "Parameters deleted successfully"}

@router.post("/sync-general")
async def sync_general_parameters(
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    try:
        from scripts.seed_parameters import seed_parameters
        await seed_parameters(force=True)
        return {"message": "General parameters synced successfully"}
    except Exception as e:
        logger.error(f"Failed to sync general parameters: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


def parse_guideline_types(val, active_types: List[str]) -> List[str]:
    if not val or pd.isna(val):
        return ["All"]
    val_str = str(val).strip()
    if val_str.lower() in ["all", "any", "*"]:
        return ["All"]
    
    parts = [p.strip() for p in re.split(r'[,;]', val_str) if p.strip()]
    
    matched = []
    active_type_map = {t.lower(): t for t in active_types}
    for part in parts:
        part_lower = part.lower()
        if part_lower in active_type_map:
            matched.append(active_type_map[part_lower])
        elif "full" in part_lower:
            if "Full Doc" in active_types:
                matched.append("Full Doc")
        elif "alt" in part_lower:
            if "Alt Doc" in active_types:
                matched.append("Alt Doc")
        elif "dscr" in part_lower:
            if "DSCR" in active_types:
                matched.append("DSCR")
                
    if not matched:
        return ["All"]
    return matched


@router.post("/bulk-upload-excel")
async def bulk_upload_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"Failed to parse Excel file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {str(e)}")
        
    # Define acceptable variations for headers (all lowercase)
    valid_header_maps = [
        {"name": "parameters", "alternatives": ["parameters", "parameter"]},
        {"name": "Category", "alternatives": ["category", "categories"]},
        {"name": "sub-Catagories", "alternatives": ["sub-catagories", "sub-categories", "subcategory", "subcategories", "sub category", "sub-category"]},
        {"name": "guideline type", "alternatives": ["guideline type", "guideline-type", "guideline_type", "guideline compatibility"]}
    ]
    
    if len(df.columns) < 4:
        raise HTTPException(
            status_code=400,
            detail="Excel file must contain at least 4 columns: 'parameters', 'Category', 'sub-Catagories', and 'guideline type'."
        )
        
    actual_headers_normalized = [str(c).strip().lower() for c in df.columns]
    
    for i in range(4):
        allowed_variations = valid_header_maps[i]["alternatives"]
        if actual_headers_normalized[i] not in allowed_variations:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid header structure. Column {i+1} must be '{valid_header_maps[i]['name']}' (case-insensitive), but found '{df.columns[i]}'."
            )
            
    # Fetch active guideline types from DB
    gtype_result = await db.execute(select(GuidelineType.name))
    active_types = gtype_result.scalars().all()
    if not active_types:
        active_types = ["DSCR", "Full Doc", "Alt Doc"]
        
    # Fetch all existing general parameters (where investor_id is None)
    existing_result = await db.execute(
        select(DSCRParameter).where(DSCRParameter.investor_id == None)
    )
    existing_params = existing_result.scalars().all()
    
    existing_map = {}
    for p in existing_params:
        key = (p.category.strip().lower(), p.parameter.strip().lower())
        existing_map[key] = p
        
    added_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    
    new_params = []
    
    for index, row in df.iterrows():
        param_val = row[df.columns[0]]
        cat_val = row[df.columns[1]]
        subcat_val = row[df.columns[2]]
        gtype_val = row[df.columns[3]]
        
        if pd.isna(param_val) or not str(param_val).strip():
            skipped_count += 1
            errors.append(f"Row {index + 2}: 'parameters' value is empty. Skipped.")
            continue
            
        if pd.isna(cat_val) or not str(cat_val).strip():
            skipped_count += 1
            errors.append(f"Row {index + 2}: 'Category' value is empty. Skipped.")
            continue
            
        param_name = str(param_val).strip()
        cat_name = str(cat_val).strip()
        subcat_name = str(subcat_val).strip() if pd.notna(subcat_val) and str(subcat_val).strip() else "Feature Eligibility"
        
        parsed_gtypes = parse_guideline_types(gtype_val, active_types)
        
        key = (cat_name.lower(), param_name.lower())
        
        if key in existing_map:
            db_param = existing_map[key]
            db_param.subcategory = subcat_name
            db_param.guideline_type = parsed_gtypes
            db_param.is_active = True
            updated_count += 1
        else:
            new_param = DSCRParameter(
                parameter=param_name,
                category=cat_name,
                subcategory=subcat_name,
                guideline_type=parsed_gtypes,
                investor_id=None,
                is_active=True
            )
            new_params.append(new_param)
            existing_map[key] = new_param
            added_count += 1
            
    if new_params:
        db.add_all(new_params)
        
    await db.commit()
    
    return {
        "message": f"Successfully processed Excel file. Added {added_count}, updated {updated_count}, skipped {skipped_count}.",
        "added_count": added_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors
    }

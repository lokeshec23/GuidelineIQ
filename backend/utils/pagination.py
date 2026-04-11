
# backend/utils/pagination.py
from typing import Generic, List, TypeVar, Optional, Any, Dict, Union
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
import json

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    pageSize: int = Field(10, ge=1)
    search: Optional[str] = None
    filters: Optional[str] = None  # JSON string from frontend
    sortField: Optional[str] = None
    sortOrder: Optional[str] = None # 'ascend', 'descend', or None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    pageSize: int

def apply_query_filters(
    query,
    model: Any,
    params: Union[PaginationParams, Dict[str, Any]],
    search_fields: List[str] = []
):
    """
    Applies search and column filters to a SQLAlchemy query.
    Used by both paginated and non-paginated (e.g. ID list) endpoints.
    """
    if isinstance(params, dict):
        params = PaginationParams(**params)

    # 1. Apply Search (Across specified fields)
    if params.search and search_fields:
        search_filters = []
        search_term = f"%{params.search}%"
        for field_name in search_fields:
            if hasattr(model, field_name):
                field = getattr(model, field_name)
                # Cast to String for safer LIKE operations if needed
                search_filters.append(cast(field, String).ilike(search_term))
        if search_filters:
            query = query.where(or_(*search_filters))

    # 2. Apply Specialized Filters (Column-level)
    if params.filters:
        try:
            filters_dict = json.loads(params.filters) if isinstance(params.filters, str) else params.filters
            for field_name, values in filters_dict.items():
                if values is not None and hasattr(model, field_name):
                    field = getattr(model, field_name)
                    if isinstance(values, list):
                        if len(values) > 0:
                            if field_name == "guideline_type":
                                # Special handling for guideline_type JSON array
                                type_filters = [cast(field, String).ilike(f"%{v}%") for v in values]
                                type_filters.append(cast(field, String).ilike("%All%"))
                                query = query.where(or_(*type_filters))
                            else:
                                query = query.where(field.in_(values))
                    else:
                        if field_name == "guideline_type":
                            query = query.where(or_(
                                cast(field, String).ilike(f"%{values}%"),
                                cast(field, String).ilike("%All%")
                            ))
                        else:
                            query = query.where(field == values)
        except Exception as e:
            print(f"Error applying filters: {e}")
    
    return query

async def paginate_query(
    db: AsyncSession,
    query,
    model: Any,
    params: Union[PaginationParams, Dict[str, Any]],
    search_fields: List[str] = []
):
    """
    Applies search, specific column filters, sorting, and pagination to a SQLAlchemy query.
    """
    if isinstance(params, dict):
        params = PaginationParams(**params)

    # 1 & 2. Apply Search and Filters via helper
    query = apply_query_filters(query, model, params, search_fields)

    # 3. Get Total Count Before Pagination
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 4. Apply Sorting
    if params.sortField and hasattr(model, params.sortField):
        sort_col = getattr(model, params.sortField)
        if params.sortOrder == 'descend':
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())
    elif hasattr(model, 'created_at'):
        query = query.order_by(model.created_at.desc())
    elif hasattr(model, 'id'):
        query = query.order_by(model.id)

    # 5. Apply Pagination
    limit = params.pageSize
    offset = (params.page - 1) * params.pageSize
    query = query.offset(offset).limit(limit)

    # 6. Execute Final Query
    result = await db.execute(query)
    items = result.scalars().unique().all()

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "pageSize": params.pageSize
    }


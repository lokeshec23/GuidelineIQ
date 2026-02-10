from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DSCRParameterBase(BaseModel):
    parameter: str
    category: str
    subcategory: str
    ppe_field: Optional[str] = None

class DSCRParameterCreate(DSCRParameterBase):
    pass

class DSCRParameterUpdate(BaseModel):
    parameter: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    ppe_field: Optional[str] = None

class DSCRParameterResponse(DSCRParameterBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

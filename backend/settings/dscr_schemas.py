from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime

GUIDELINE_TYPE_OPTIONS = ["All", "DSCR", "Full Doc", "Alt Doc"]

class DSCRParameterBase(BaseModel):
    parameter: str
    category: str
    subcategory: Optional[str] = "Feature Eligibility"
    ppe_field: Optional[str] = None
    guideline_type: List[str] = ["All"]
    investor_id: Optional[str] = None

    @field_validator("guideline_type", mode="before")
    @classmethod
    def process_guideline_type(cls, v):
        if v is None:
            return ["All"]
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return [v]
        return v

class DSCRParameterCreate(DSCRParameterBase):
    pass

class DSCRParameterUpdate(BaseModel):
    parameter: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    ppe_field: Optional[str] = None
    guideline_type: Optional[List[str]] = None
    investor_id: Optional[str] = None

class DSCRParameterResponse(DSCRParameterBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

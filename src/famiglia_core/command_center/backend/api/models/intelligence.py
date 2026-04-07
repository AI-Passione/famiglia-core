from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class IntelligenceItemBase(BaseModel):
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    item_type: str # 'dossier', 'blueprint'
    reference_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IntelligenceItemCreate(IntelligenceItemBase):
    pass

class IntelligenceItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    item_type: Optional[str] = None
    reference_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class IntelligenceItem(IntelligenceItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class IntelligenceItemBase(BaseModel):
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    item_type: str # 'dossier', 'blueprint'
    notion_id: Optional[UUID] = None
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    parent: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    public_url: Optional[str] = None
    in_trash: bool = False
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    created_by: Optional[Dict[str, Any]] = None
    last_edited_by: Optional[Dict[str, Any]] = None

class IntelligenceItemCreate(IntelligenceItemBase):
    pass

class IntelligenceItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    item_type: Optional[str] = None
    notion_id: Optional[UUID] = None
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    parent: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    public_url: Optional[str] = None
    in_trash: Optional[bool] = None
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None

class IntelligenceItem(IntelligenceItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

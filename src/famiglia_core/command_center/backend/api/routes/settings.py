from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from famiglia_core.command_center.backend.api.services.user_service import user_service

router = APIRouter(prefix="/settings", tags=["settings"])

class AppSettingsPayload(BaseModel):
    honorific: str = Field(default="Don", min_length=1, max_length=64)
    notificationsEnabled: bool = True
    backgroundAnimationsEnabled: bool = True


@router.get("/")
async def get_settings():
    try:
        return user_service.get_don_settings()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {exc}")


@router.put("/")
async def update_settings(payload: AppSettingsPayload):
    try:
        return user_service.update_don_settings(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist settings: {exc}")

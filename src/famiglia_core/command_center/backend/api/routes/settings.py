import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "honorific": "Don",
    "notificationsEnabled": True,
    "backgroundAnimationsEnabled": True,
}

SETTINGS_FILE_PATH = os.getenv(
    "COMMAND_CENTER_SETTINGS_FILE",
    os.path.abspath(os.path.join(os.getcwd(), "data/command_center_settings.json")),
)


class AppSettingsPayload(BaseModel):
    honorific: str = Field(default="Don", min_length=1, max_length=64)
    notificationsEnabled: bool = True
    backgroundAnimationsEnabled: bool = True


def _read_settings_from_disk() -> dict:
    if not os.path.exists(SETTINGS_FILE_PATH):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as settings_file:
            parsed = json.load(settings_file)
            return {
                "honorific": parsed.get("honorific", DEFAULT_SETTINGS["honorific"]),
                "notificationsEnabled": parsed.get(
                    "notificationsEnabled", DEFAULT_SETTINGS["notificationsEnabled"]
                ),
                "backgroundAnimationsEnabled": parsed.get(
                    "backgroundAnimationsEnabled",
                    DEFAULT_SETTINGS["backgroundAnimationsEnabled"],
                ),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read settings: {exc}")


def _write_settings_to_disk(settings_payload: AppSettingsPayload) -> None:
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE_PATH), exist_ok=True)
        with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as settings_file:
            json.dump(settings_payload.model_dump(), settings_file, indent=2)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist settings: {exc}")


@router.get("/")
async def get_settings():
    return _read_settings_from_disk()


@router.put("/")
async def update_settings(payload: AppSettingsPayload):
    _write_settings_to_disk(payload)
    return payload.model_dump()

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.health import ServiceHealth

router = APIRouter()


@router.get("/health", response_model=ServiceHealth)
def health() -> ServiceHealth:
    return ServiceHealth(status="ok", mode=get_settings().procore_mode)


@router.get("/ready", response_model=ServiceHealth)
def ready() -> ServiceHealth:
    return ServiceHealth(status="ready", mode=get_settings().procore_mode)


@router.get("/safety")
def safety() -> dict:
    return {
        "read_only": True,
        "procore_writes": False,
        "live_procore_calls": False,
        "message": "Phase A1 never writes to Procore and uses local fixtures only.",
    }

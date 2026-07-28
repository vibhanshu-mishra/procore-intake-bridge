from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.schemas.health import ServiceHealth
from app.services.deployment_readiness import build_deployment_readiness_report

router = APIRouter()


@router.get("/health", response_model=ServiceHealth)
def health() -> ServiceHealth:
    return ServiceHealth(status="ok", mode=get_settings().procore_mode)


@router.get("/ready")
def ready(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    database_ok = True
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        database_ok = False
    report = build_deployment_readiness_report(settings)
    target_ready = {
        "local": report.ready_for_local,
        "staging": report.ready_for_staging,
        "production": report.ready_for_production,
    }[settings.environment]
    return {
        "status": "ready" if database_ok and target_ready else "not_ready",
        "mode": settings.procore_mode,
        "database_connected": database_ok,
        "deployment": {
            "environment": report.environment,
            "ready_for_environment": target_ready,
            "ready_for_production": report.ready_for_production,
            "blocking_findings_count": report.blocking_findings_count,
            "warning_findings_count": report.warning_findings_count,
        },
    }


@router.get("/safety")
def safety() -> dict:
    return {
        "read_only": True,
        "procore_writes": False,
        "live_procore_calls": False,
        "message": "Phase A1 never writes to Procore and uses local fixtures only.",
    }

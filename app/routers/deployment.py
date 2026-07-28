from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.security.secret_provider_factory import summarize_secret_provider_config
from app.services.deployment_readiness import (
    build_deployment_readiness_report,
    build_sanitized_config_summary,
)
from app.services.secret_inventory import collect_required_secret_refs

router = APIRouter(prefix="/deployment", tags=["deployment"])


@router.get("/readiness")
def deployment_readiness() -> dict:
    return build_deployment_readiness_report(get_settings()).model_dump(mode="json")


@router.get("/safety")
def deployment_safety() -> dict:
    settings = get_settings()
    report = build_deployment_readiness_report(settings)
    return {
        "environment": settings.environment,
        "read_only_procore": True,
        "procore_writes": False,
        "live_mode_enabled": settings.procore_live_mode_enabled,
        "fixture_only_downloads": settings.attachment_fixture_downloads_only,
        "production_ready": report.ready_for_production,
        "blocking_findings_count": report.blocking_findings_count,
    }


@router.get("/config-summary")
def deployment_config_summary() -> dict:
    return build_sanitized_config_summary(get_settings())


@router.get("/secrets")
def deployment_secrets(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    inventory = collect_required_secret_refs(
        settings, db_session=session, run_health=True
    )
    return {
        "provider": summarize_secret_provider_config(settings),
        "required_refs": [item.model_dump() for item in inventory],
        "required_refs_count": len(inventory),
        "missing_refs_count": sum(item.status == "missing" for item in inventory),
        "values_exposed": False,
    }

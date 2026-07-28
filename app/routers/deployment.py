from fastapi import APIRouter

from app.config import get_settings
from app.services.deployment_readiness import (
    build_deployment_readiness_report,
    build_sanitized_config_summary,
)

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

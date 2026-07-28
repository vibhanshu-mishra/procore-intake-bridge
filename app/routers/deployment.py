from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.security.admin_access import (
    ADMIN_SECURITY_HEADERS,
    AdminAccessError,
    add_admin_security_headers,
    require_admin_access,
    sanitize_admin_auth_error,
)
from app.security.secret_provider_factory import (
    build_secret_provider,
    summarize_secret_provider_config,
)
from app.services.deployment_readiness import (
    build_deployment_readiness_report,
    build_sanitized_config_summary,
)
from app.services.migration_status import build_migration_status_report
from app.services.secret_inventory import collect_required_secret_refs


def deployment_operator_guard(
    request: Request, response: Response
) -> Settings:
    settings = get_settings()
    if settings.admin_auth_protect_deployment_routes:
        try:
            require_admin_access(
                request, settings, build_secret_provider(settings)
            )
        except AdminAccessError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=sanitize_admin_auth_error(exc),
                headers=ADMIN_SECURITY_HEADERS,
            ) from exc
        add_admin_security_headers(response)
    return settings


router = APIRouter(
    prefix="/deployment",
    tags=["deployment"],
    dependencies=[Depends(deployment_operator_guard)],
)


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


@router.get("/migrations")
def deployment_migrations() -> dict:
    return build_migration_status_report(get_settings()).model_dump(mode="json")

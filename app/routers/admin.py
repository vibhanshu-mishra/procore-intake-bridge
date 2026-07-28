from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.admin import (
    AdminOverview,
    AdminRecentAttachment,
    AdminRecentConnection,
    AdminRecentIntakeRecord,
    AdminRecentOnboardingPacket,
    AdminRecentSyncProfile,
    AdminRecentSyncRun,
    AdminRecentWebhookEvent,
    AdminSafetyStatus,
)
from app.security.admin_access import AdminAccessError, require_admin_access
from app.security.secret_provider import EnvSecretProvider
from app.services.admin_dashboard import (
    build_admin_overview,
    build_attachment_summary,
    build_connection_summary,
    build_intake_record_summary,
    build_onboarding_packet_summary,
    build_safety_status,
    build_sync_profile_summary,
    build_sync_run_summary,
    build_webhook_event_summary,
)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)


def admin_guard(request: Request) -> Settings:
    settings = get_settings()
    try:
        require_admin_access(request, settings, EnvSecretProvider())
    except AdminAccessError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc
    return settings


def _limit(
    settings: Settings, limit: int | None, page_size: int | None
) -> int:
    requested = limit if limit is not None else page_size
    return min(requested or settings.admin_page_size, 100)


@router.get("/api/overview", response_model=AdminOverview)
def api_overview(
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_admin_overview(session, settings)


@router.get("/api/connections", response_model=list[AdminRecentConnection])
def api_connections(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_connection_summary(session, _limit(settings, limit, page_size))


@router.get(
    "/api/sync-profiles", response_model=list[AdminRecentSyncProfile]
)
def api_sync_profiles(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_sync_profile_summary(
        session, _limit(settings, limit, page_size)
    )


@router.get("/api/sync-runs", response_model=list[AdminRecentSyncRun])
def api_sync_runs(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_sync_run_summary(session, _limit(settings, limit, page_size))


@router.get(
    "/api/intake-records", response_model=list[AdminRecentIntakeRecord]
)
def api_intake_records(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_intake_record_summary(
        session, _limit(settings, limit, page_size)
    )


@router.get("/api/attachments", response_model=list[AdminRecentAttachment])
def api_attachments(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_attachment_summary(
        session, _limit(settings, limit, page_size)
    )


@router.get(
    "/api/webhook-events", response_model=list[AdminRecentWebhookEvent]
)
def api_webhook_events(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_webhook_event_summary(
        session, _limit(settings, limit, page_size)
    )


@router.get(
    "/api/onboarding-packets",
    response_model=list[AdminRecentOnboardingPacket],
)
def api_onboarding_packets(
    limit: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_onboarding_packet_summary(
        session, _limit(settings, limit, page_size)
    )


@router.get("/api/safety", response_model=AdminSafetyStatus)
def api_safety(settings: Settings = Depends(admin_guard)):
    return build_safety_status(settings)


@router.get("")
def html_overview(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    overview = build_admin_overview(session, settings)
    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={"overview": overview, "title": "Overview"},
    )


@router.get("/safety")
def html_safety(
    request: Request, settings: Settings = Depends(admin_guard)
):
    return templates.TemplateResponse(
        request=request,
        name="admin/safety.html",
        context={"safety": build_safety_status(settings), "title": "Safety"},
    )


@router.get("/connections")
def html_connections(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Connections",
        build_connection_summary(session, settings.admin_page_size),
        "No connections yet",
    )


@router.get("/sync-profiles")
def html_sync_profiles(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Sync profiles",
        build_sync_profile_summary(session, settings.admin_page_size),
        "No sync profiles yet",
    )


@router.get("/sync-runs")
def html_sync_runs(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Sync runs",
        build_sync_run_summary(session, settings.admin_page_size),
        "No sync runs yet",
    )


@router.get("/intake-records")
def html_intake_records(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Intake records",
        build_intake_record_summary(session, settings.admin_page_size),
        "No intake records yet",
    )


@router.get("/attachments")
def html_attachments(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Attachment manifests",
        build_attachment_summary(session, settings.admin_page_size),
        "No attachment manifests yet",
    )


@router.get("/webhook-events")
def html_webhook_events(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Webhook events",
        build_webhook_event_summary(session, settings.admin_page_size),
        "No webhook events yet",
    )


@router.get("/onboarding-packets")
def html_onboarding_packets(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return _list_page(
        request,
        "Onboarding packets",
        build_onboarding_packet_summary(session, settings.admin_page_size),
        "No onboarding packets yet",
    )


def _list_page(request: Request, title: str, rows: list, empty: str):
    safe_rows = [row.model_dump(mode="json") for row in rows]
    columns = list(safe_rows[0]) if safe_rows else []
    return templates.TemplateResponse(
        request=request,
        name="admin/list.html",
        context={
            "title": title,
            "rows": safe_rows,
            "columns": columns,
            "empty_message": empty,
        },
    )

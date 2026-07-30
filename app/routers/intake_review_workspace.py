from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_session
from app.routers.admin import admin_guard
from app.schemas.intake_lifecycle import (
    IntakeLifecycleHistoryPage,
    IntakeLifecycleStateView,
    IntakeLifecycleTransitionRequest,
    IntakeLifecycleTransitionResult,
)
from app.schemas.intake_review_workspace import (
    IntakeReviewRecordDetail,
    IntakeReviewWorkspacePage,
    IntakeReviewWorkspaceSummary,
)
from app.schemas.operator_triage_queue import (
    OperatorTriageQueuePage,
    OperatorTriageQueueSummary,
)
from app.services.intake_lifecycle import (
    IntakeLifecycleBlockedError,
    IntakeLifecycleError,
    apply_lifecycle_transition,
    get_lifecycle_state,
    list_lifecycle_history,
)
from app.services.intake_review_workspace import (
    IntakeReviewWorkspaceError,
    build_intake_review_filter,
    build_intake_review_workspace_summary,
    get_intake_review_record_detail,
    list_intake_review_records,
)
from app.services.operator_triage_queue import (
    OperatorTriageQueueError,
    build_operator_triage_filter,
    build_operator_triage_summary,
    list_operator_triage_queue,
)

router = APIRouter(prefix="/review", tags=["intake-review"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _filters(
    settings: Settings,
    tool: str | None,
    page: int,
    page_size: int | None,
    sort: str | None,
):
    try:
        return build_intake_review_filter(
            settings, tool=tool, page=page, page_size=page_size, sort=sort
        )
    except IntakeReviewWorkspaceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _lifecycle_error(exc: IntakeLifecycleError) -> HTTPException:
    status = 403 if isinstance(exc, IntakeLifecycleBlockedError) else 400
    if "not found" in str(exc).casefold():
        status = 404
    return HTTPException(status_code=status, detail=str(exc))


def _triage_filters(
    settings: Settings,
    bucket: str | None,
    tool: str | None,
    lifecycle_status: str | None,
    page: int,
    page_size: int | None,
    sort: str | None,
):
    try:
        return build_operator_triage_filter(
            settings,
            bucket=bucket,
            tool=tool,
            lifecycle_status=lifecycle_status,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    except OperatorTriageQueueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/summary", response_model=IntakeReviewWorkspaceSummary)
def api_summary(
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_intake_review_workspace_summary(session, settings)


@router.get("/api/intake", response_model=IntakeReviewWorkspacePage)
def api_intake(
    tool: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    sort: str | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return list_intake_review_records(
        session, _filters(settings, tool, page, page_size, sort), settings
    )


@router.get("/api/intake/{record_id}", response_model=IntakeReviewRecordDetail)
def api_intake_detail(
    record_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    try:
        detail = get_intake_review_record_detail(session, record_id, settings)
    except IntakeReviewWorkspaceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Local intake record not found.")
    return detail


@router.get("")
def html_review(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    summary = build_intake_review_workspace_summary(session, settings)
    return templates.TemplateResponse(
        request=request,
        name="review/index.html",
        context={"title": "Intake Review Workspace", "summary": summary},
    )


@router.get("/intake")
def html_intake(
    request: Request,
    tool: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    sort: str | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    result = list_intake_review_records(
        session, _filters(settings, tool, page, page_size, sort), settings
    )
    return templates.TemplateResponse(
        request=request,
        name="review/list.html",
        context={"title": "Local intake records", "page": result},
    )


@router.get("/intake/{record_id}")
def html_intake_detail(
    record_id: int,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    try:
        detail = get_intake_review_record_detail(session, record_id, settings)
    except IntakeReviewWorkspaceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Local intake record not found.")
    return templates.TemplateResponse(
        request=request,
        name="review/detail.html",
        context={"title": "Intake record detail", "record": detail},
    )


@router.get(
    "/api/intake/{record_id}/lifecycle",
    response_model=IntakeLifecycleStateView,
)
def api_lifecycle_state(
    record_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    try:
        return get_lifecycle_state(session, record_id, settings)
    except IntakeLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.get(
    "/api/intake/{record_id}/lifecycle/history",
    response_model=IntakeLifecycleHistoryPage,
)
def api_lifecycle_history(
    record_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    try:
        return list_lifecycle_history(session, record_id, page, page_size, settings)
    except IntakeLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.post(
    "/api/intake/{record_id}/lifecycle",
    response_model=IntakeLifecycleTransitionResult,
)
def api_lifecycle_transition(
    record_id: int,
    payload: IntakeLifecycleTransitionRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    try:
        return apply_lifecycle_transition(session, record_id, payload, settings)
    except IntakeLifecycleError as exc:
        raise _lifecycle_error(exc) from exc


@router.get("/intake/{record_id}/lifecycle/history")
def html_lifecycle_history(
    record_id: int,
    request: Request,
    page: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    try:
        history = list_lifecycle_history(session, record_id, page, 25, settings)
    except IntakeLifecycleError as exc:
        raise _lifecycle_error(exc) from exc
    return templates.TemplateResponse(
        request=request,
        name="review/history.html",
        context={
            "title": "Local lifecycle history",
            "record_id": record_id,
            "history": history,
        },
    )


@router.post("/intake/{record_id}/lifecycle")
async def html_lifecycle_transition(
    record_id: int,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    fields = parse_qs((await request.body()).decode("utf-8"))
    try:
        payload = IntakeLifecycleTransitionRequest(
            to_status=fields.get("to_status", [""])[0],
            reason_code=fields.get("reason_code", [""])[0],
            actor_label="LOCAL_OPERATOR_PLACEHOLDER",
        )
        apply_lifecycle_transition(session, record_id, payload, settings)
    except (IntakeLifecycleError, ValueError) as exc:
        lifecycle_exc = (
            exc
            if isinstance(exc, IntakeLifecycleError)
            else IntakeLifecycleError("Invalid local lifecycle request.")
        )
        raise _lifecycle_error(lifecycle_exc) from exc
    return RedirectResponse(url=f"/review/intake/{record_id}", status_code=303)


@router.get("/api/triage", response_model=OperatorTriageQueuePage)
def api_triage_queue(
    bucket: str | None = None,
    tool: str | None = None,
    lifecycle_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    sort: str | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    filters = _triage_filters(settings, bucket, tool, lifecycle_status, page, page_size, sort)
    return list_operator_triage_queue(session, filters, settings)


@router.get("/api/triage/summary", response_model=OperatorTriageQueueSummary)
def api_triage_summary(
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_operator_triage_summary(session, settings)


@router.get("/triage")
def html_triage_queue(
    request: Request,
    bucket: str | None = None,
    tool: str | None = None,
    lifecycle_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    sort: str | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    filters = _triage_filters(settings, bucket, tool, lifecycle_status, page, page_size, sort)
    return templates.TemplateResponse(
        request=request,
        name="review/triage.html",
        context={
            "title": "Operator Triage Queue",
            "queue": list_operator_triage_queue(session, filters, settings),
            "summary": build_operator_triage_summary(session, settings),
        },
    )

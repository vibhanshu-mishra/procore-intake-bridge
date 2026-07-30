from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_session
from app.routers.admin import admin_guard
from app.schemas.intake_review_workspace import (
    IntakeReviewRecordDetail,
    IntakeReviewWorkspacePage,
    IntakeReviewWorkspaceSummary,
)
from app.services.intake_review_workspace import (
    IntakeReviewWorkspaceError,
    build_intake_review_filter,
    build_intake_review_workspace_summary,
    get_intake_review_record_detail,
    list_intake_review_records,
)

router = APIRouter(prefix="/review", tags=["intake-review"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)


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

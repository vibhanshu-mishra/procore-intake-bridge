from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_session
from app.routers.admin import admin_guard
from app.schemas.product_dashboard import ProductDashboardOverview
from app.services.product_dashboard import build_product_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["product-dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/api/overview", response_model=ProductDashboardOverview)
def api_overview(
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return build_product_dashboard_overview(session, settings)


@router.get("")
def html_overview(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(admin_guard),
):
    return templates.TemplateResponse(
        request=request,
        name="product_dashboard/index.html",
        context={
            "overview": build_product_dashboard_overview(session, settings),
            "title": "Product Dashboard",
        },
    )

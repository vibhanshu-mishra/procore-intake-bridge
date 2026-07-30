from pathlib import Path
from subprocess import run

import pytest

from app.config import Settings
from app.main import app
from app.routers.admin import admin_guard
from app.schemas.product_dashboard import ProductDashboardCardStatus
from app.services.product_dashboard import (
    ProductDashboardError,
    build_product_dashboard_overview,
    render_product_dashboard_markdown,
    validate_product_dashboard_response_safe,
)
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def test_empty_dashboard_has_all_safe_card_groups(db_session):
    overview = build_product_dashboard_overview(db_session, _settings())
    assert {card.group for card in overview.cards} == {
        "system",
        "intake_review",
        "lifecycle",
        "triage",
        "attachments",
        "exports",
        "sandbox",
        "pilot",
        "safety",
    }
    assert overview.read_only is True
    assert overview.local_database_only is True
    assert overview.procore_calls_made is False
    assert overview.database_writes_made is False
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_cards_use_safe_aggregate_and_guidance_language(db_session):
    overview = build_product_dashboard_overview(db_session, _settings())
    cards = {card.group: card for card in overview.cards}
    assert cards["triage"].message == "Deterministic local sorting helper only."
    assert "metadata-only" in cards["attachments"].message.casefold()
    assert all(link.href is None for link in cards["exports"].links)
    assert {link.command for link in cards["exports"].links} == {
        "make operator-export-check",
        "make operator-export-summary",
    }
    assert "private" in cards["sandbox"].message.casefold()
    assert "gated" in cards["pilot"].message.casefold()
    rendered = overview.model_dump_json().casefold()
    for forbidden in ("filename", "storage_key", "raw_payload", "approval granted"):
        assert forbidden not in rendered


def test_dashboard_fails_closed_for_unsafe_settings(db_session):
    overview = build_product_dashboard_overview(
        db_session, _settings(product_dashboard_expose_raw_payloads=True)
    )
    assert overview.cards[0].status is ProductDashboardCardStatus.NEEDS_CONFIGURATION


@pytest.mark.parametrize(
    "unsafe",
    [
        {"raw_payload_json": {"fake": True}},
        {"source_url": "hidden"},
        {"signed_url": "hidden"},
        {"storage_key": "hidden"},
        {"filename": "hidden"},
        {"message": "https://unsafe.invalid/value"},
        {"message": "/Users/example/private"},
        {"message": "client_secret=unsafe"},
    ],
)
def test_safety_validator_blocks_unsafe_content(unsafe):
    with pytest.raises(ProductDashboardError):
        validate_product_dashboard_response_safe(unsafe)


def test_markdown_is_command_only_and_sanitized(db_session):
    rendered = render_product_dashboard_markdown(
        build_product_dashboard_overview(db_session, _settings())
    )
    assert "make operator-export-check" in rendered
    assert "No artifact was generated" in rendered
    assert "attachment file was read" in rendered
    assert "authorization" in rendered


def test_get_only_routes_and_guard(client):
    assert client.get("/dashboard").status_code == 200
    response = client.get("/dashboard/api/overview")
    assert response.status_code == 200
    assert response.json()["external_calls_made"] is False
    routes = {
        route.path: route.methods
        for route in application_routes()
        if route.path.startswith("/dashboard")
    }
    assert routes == {
        "/dashboard": {"GET"},
        "/dashboard/api/overview": {"GET"},
    }
    assert audit_routes() == []

    def disabled():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Dashboard disabled.")

    app.dependency_overrides[admin_guard] = disabled
    assert client.get("/dashboard").status_code == 404
    app.dependency_overrides.pop(admin_guard)


def test_template_links_product_surfaces_without_generated_files(client):
    body = client.get("/dashboard").text
    for target in ("/review", "/review/triage", "/review/attachments"):
        assert target in body
    assert "make operator-export-check" in body
    assert "operator-export-output" not in body
    assert 'href="/download' not in body.casefold()


def test_cli_and_make_targets_run():
    for command in (
        [".venv/bin/python", "scripts/check_product_dashboard.py"],
        [".venv/bin/python", "scripts/print_product_dashboard_overview.py"],
        ["make", "product-dashboard-check"],
        ["make", "product-dashboard-overview"],
    ):
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr

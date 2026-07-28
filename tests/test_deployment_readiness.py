import json
from pathlib import Path

import pytest

from app.config import Settings
from app.services.deployment_readiness import (
    build_deployment_readiness_report,
    build_sanitized_config_summary,
)
from app.services.startup_checks import StartupCheckError, run_startup_checks


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_local_environment_is_locally_ready():
    report = build_deployment_readiness_report(make_settings())
    assert report.ready_for_local is True
    assert report.ready_for_production is False


@pytest.mark.parametrize(
    "overrides, check",
    [
        ({"environment": "production"}, "database"),
        ({"environment": "production", "admin_require_token": False}, "admin_dashboard"),
        (
            {"environment": "production", "require_webhook_signature": False},
            "webhook_signature",
        ),
        ({"environment": "production", "allowed_hosts": "*"}, "allowed_hosts"),
    ],
)
def test_unsafe_production_settings_are_blocking(overrides, check):
    report = build_deployment_readiness_report(make_settings(**overrides))
    assert report.ready_for_production is False
    assert any(f.check == check and f.severity == "blocking" for f in report.findings)


def test_config_summary_masks_database_credentials_and_secret_references():
    secret = "do-not-leak"
    configured = make_settings(
        database_url=f"postgresql://user:{secret}@db.example/app",
        webhook_secret_name="reference-only",
        admin_token_secret_name="reference-only",
    )
    summary = build_sanitized_config_summary(configured)
    serialized = json.dumps(summary)
    assert secret not in serialized
    assert "***" in summary["database_url"]
    assert "reference-only" not in serialized


def test_startup_checks_fail_closed_without_leaking_secret():
    secret = "never-print-this"
    configured = make_settings(
        environment="production",
        database_url=f"postgresql://user:{secret}@db.example/app",
    )
    with pytest.raises(StartupCheckError) as error:
        run_startup_checks(configured)
    assert secret not in str(error.value)


def test_unsafe_production_can_report_without_raising():
    report = run_startup_checks(
        make_settings(environment="production", fail_startup_on_unsafe_production=False)
    )
    assert report.blocking_findings_count > 0


def test_deployment_assets_are_safe():
    dockerignore = Path(".dockerignore").read_text()
    compose = Path("docker-compose.yml").read_text().lower()
    docs = Path("docs/deployment-hardening.md").read_text().lower()
    assert ".env" in dockerignore
    assert "packet-output" in dockerignore
    assert "replace_me" not in compose
    assert "local-dev only" in docs
    assert "production security certification" in docs

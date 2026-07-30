from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.security_threat_model import SecurityThreatCategory
from app.services.security_threat_model import (
    BOUNDARY_NAMES,
    IGNORED_OUTPUTS,
    SecurityThreatModelBlockedError,
    build_security_threat_model_report,
    render_security_boundary_map,
    render_security_review_checklist,
    render_security_threat_model_markdown,
    validate_security_threat_model_report_safe,
    write_security_threat_model_artifacts,
)
from scripts.audit_public_safety import audit_text

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_report_covers_categories_boundaries_and_controls_offline():
    report = build_security_threat_model_report(_settings())
    assert report.status == "ready"
    assert report.decision == "threat_model_ready_for_security_review"
    assert {item.category for item in report.scenarios} == set(SecurityThreatCategory)
    assert tuple(item.name for item in report.boundaries) == BOUNDARY_NAMES
    assert all(item.boundary in BOUNDARY_NAMES for item in report.controls)
    assert not any(
        (
            report.live_operation_attempted,
            report.external_call_attempted,
            report.procore_call_attempted,
            report.cloud_call_attempted,
            report.db_connection_attempted,
            report.deployment_attempted,
            report.scanner_attempted,
            report.private_report_contents_exposed,
            report.secrets_exposed,
            report.ids_exposed,
            report.real_urls_exposed,
            report.real_domains_exposed,
            report.private_paths_exposed,
            report.certification_claimed,
            report.production_approval_claimed,
        )
    )
    validate_security_threat_model_report_safe(report)


@pytest.mark.parametrize(
    "override",
    (
        {"security_threat_model_require_placeholders": False},
        {"security_threat_model_allow_real_identities": True},
        {"security_threat_model_allow_real_domains": True},
        {"security_threat_model_allow_real_urls": True},
        {"security_threat_model_allow_report_contents": True},
        {"security_threat_model_allow_private_paths": True},
    ),
)
def test_unsafe_settings_fail_closed(override):
    with pytest.raises(SecurityThreatModelBlockedError):
        build_security_threat_model_report(_settings(**override))


@pytest.mark.parametrize(
    "unsafe",
    (
        {"source_url": "placeholder"},
        {"message": "https://unsafe.invalid/report"},
        {"message": "reviewer@example.com"},
        {"message": "/Users/example/private"},
        {"message": "Authorization: Bearer raw-token-value"},
        {"message": "raw report contents"},
        {"message": "The system is production-ready"},
        {"message": "Security certified"},
    ),
)
def test_validator_blocks_private_material_and_unsafe_claims(unsafe):
    with pytest.raises(SecurityThreatModelBlockedError):
        validate_security_threat_model_report_safe(unsafe)


def test_missing_repository_inputs_need_review(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    report = build_security_threat_model_report(_settings())
    assert report.status == "needs_review"
    assert report.findings


def test_renderers_are_public_safe():
    report = build_security_threat_model_report(_settings())
    rendered = "\n".join(
        (
            render_security_threat_model_markdown(report),
            render_security_boundary_map(report),
            render_security_review_checklist(report),
        )
    )
    assert "No live scanner" in rendered
    assert "not production authorization" in rendered
    assert "generated_output_boundary" in rendered
    validate_security_threat_model_report_safe(rendered)


def test_artifact_roots_fail_closed():
    report = build_security_threat_model_report(_settings())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-security-review")):
        with pytest.raises(SecurityThreatModelBlockedError):
            write_security_threat_model_artifacts(report, path)


def test_temp_artifacts_are_complete_and_safe():
    report = build_security_threat_model_report(_settings())
    with TemporaryDirectory(
        prefix="procore-intake-bridge-security-threat-model-", dir="/tmp"
    ) as directory:
        result = write_security_threat_model_artifacts(report, Path(directory))
        assert set(result.files) == {
            "manifest.json",
            "security-threat-model-report.json",
            "security-threat-model-report.md",
            "security-boundary-map.md",
            "security-review-checklist.md",
        }
        for name in result.files:
            validate_security_threat_model_report_safe(
                (Path(directory) / name).read_text(encoding="utf-8")
            )


def test_cli_and_make_targets_run():
    commands = (
        [".venv/bin/python", "scripts/run_security_threat_model.py"],
        [".venv/bin/python", "scripts/print_security_boundary_map.py"],
        [".venv/bin/python", "scripts/print_security_review_checklist.py"],
        [
            ".venv/bin/python",
            "scripts/generate_security_threat_model_artifacts.py",
            "--temporary",
        ],
        ["make", "security-threat-model"],
        ["make", "security-boundary-map"],
        ["make", "security-review-checklist"],
        ["make", "security-threat-model-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_ignore_and_quality_contracts():
    required = (
        "docs/security-threat-model.md",
        "docs/security-boundary-map.md",
        "docs/security-review-checklist.md",
        "examples/security-threat-model/README.md",
        "examples/security-threat-model/example_security_boundary_map.md",
        "examples/security-threat-model/example_security_review_checklist.md",
    )
    assert all((ROOT / path).is_file() for path in required)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(pattern in gitignore for pattern in IGNORED_OUTPUTS)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert (
        "quality: security-threat-model security-boundary-map security-review-checklist" in makefile
    )
    quality = "\n".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "security-threat-model-artifact-check" not in quality


def test_public_safety_detects_claims_and_generated_outputs(tmp_path):
    claim = tmp_path / "security-threat-model.md"
    assert audit_text(claim, "This security review is production-ready.")
    generated = tmp_path / "security-threat-model-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder", encoding="utf-8")
    from scripts.audit_public_safety import audit_paths

    assert audit_paths([generated])


def test_i1_adds_no_route_and_route_audit_remains_green():
    from scripts.audit_routes_read_only import application_routes, audit_routes

    assert not any(route.path.startswith("/security") for route in application_routes())
    assert audit_routes() == []

from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.schemas.auth_boundary_audit import (
    AuthBoundaryProtectionType,
    AuthBoundaryRouteClass,
)
from app.services.auth_boundary_audit import (
    ARTIFACT_FILES,
    IGNORED_OUTPUTS,
    LIFECYCLE_POST_PATHS,
    WEBHOOK_INGRESS_PATHS,
    AuthBoundaryAuditBlockedError,
    build_auth_boundary_audit_report,
    build_route_permission_matrix,
    classify_route_auth_boundary,
    render_auth_boundary_map_markdown,
    render_permission_boundary_checklist,
    render_route_permission_matrix_csv,
    validate_auth_boundary_audit_report_safe,
    write_auth_boundary_audit_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def _fake_route(path: str, method: str = "POST"):
    return SimpleNamespace(path=path, methods={method}, dependant=SimpleNamespace(dependencies=[]))


def test_report_builds_offline_with_expected_boundaries():
    report = build_auth_boundary_audit_report(_settings())
    assert report.status == "ready"
    assert report.decision == "auth_boundary_ready_for_security_review"
    assert report.routes_total == len(application_routes())
    assert report.public_routes_total == 3
    assert report.webhook_routes_total == 2
    assert report.unknown_routes_total == 0
    assert report.unsafe_routes_total == 0
    assert report.public_routes_are_limited
    assert report.admin_routes_protected
    assert report.review_routes_protected
    assert report.lifecycle_posts_local_only
    assert report.webhook_signature_required
    assert report.live_commands_gated
    assert not report.export_download_routes_present
    assert not report.file_serving_routes_present
    assert not report.procore_write_routes_present
    assert not any(
        (
            report.external_call_attempted,
            report.procore_call_attempted,
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
    validate_auth_boundary_audit_report_safe(report)


def test_route_and_protection_enums_cover_spec():
    assert {item.value for item in AuthBoundaryRouteClass} == {
        "public_health",
        "public_readiness",
        "protected_admin",
        "protected_deployment",
        "protected_product_dashboard",
        "protected_review_workspace",
        "protected_review_api",
        "protected_lifecycle_local_mutation",
        "webhook_signature_required",
        "docs_or_static_local",
        "unknown",
    }
    assert {item.value for item in AuthBoundaryProtectionType} >= {
        "intentionally_public",
        "admin_token_required",
        "webhook_signature_required",
        "manual_confirmation_required",
        "secret_provider_required",
        "private_workspace_required",
        "disabled_by_default",
        "local_only",
        "no_network",
        "unknown",
    }


def test_current_route_matrix_has_expected_classifications():
    matrix = build_route_permission_matrix(application_routes(), _settings())
    by_route = {(item.method, item.path): item for item in matrix}
    assert by_route[("GET", "/health")].protection_type == "intentionally_public"
    assert by_route[("GET", "/ready")].route_class == "public_readiness"
    assert by_route[("GET", "/admin")].protection_type == "admin_token_required"
    assert by_route[("GET", "/dashboard")].route_class == "protected_product_dashboard"
    assert by_route[("GET", "/review")].route_class == "protected_review_workspace"
    for path in LIFECYCLE_POST_PATHS:
        assert by_route[("POST", path)].method_risk == "local_only_post"
        assert by_route[("POST", path)].admin_guard_present
    for path in WEBHOOK_INGRESS_PATHS:
        assert by_route[("POST", path)].protection_type == "webhook_signature_required"


def test_unknown_mutation_is_unsafe_and_matrix_fails_closed():
    item = classify_route_auth_boundary(_fake_route("/unknown/mutate"))
    assert item.route_class == "unknown"
    assert item.method_risk == "unsafe_mutation"
    with pytest.raises(AuthBoundaryAuditBlockedError):
        build_route_permission_matrix([_fake_route("/unknown/mutate")], _settings())


@pytest.mark.parametrize(
    "override",
    (
        {"auth_boundary_audit_require_placeholders": False},
        {"auth_boundary_audit_require_admin_protection": False},
        {"auth_boundary_audit_allow_public_health_routes": False},
        {"auth_boundary_audit_allow_lifecycle_post_only": False},
        {"auth_boundary_audit_require_webhook_signature": False},
        {"auth_boundary_audit_require_live_command_gates": False},
        {"auth_boundary_audit_allow_real_identities": True},
        {"auth_boundary_audit_allow_real_domains": True},
        {"auth_boundary_audit_allow_real_urls": True},
        {"auth_boundary_audit_allow_report_contents": True},
        {"auth_boundary_audit_allow_private_paths": True},
    ),
)
def test_unsafe_policy_fails_closed(override):
    with pytest.raises(AuthBoundaryAuditBlockedError):
        build_auth_boundary_audit_report(_settings(**override))


@pytest.mark.parametrize(
    "unsafe",
    (
        {"source_url": "placeholder"},
        {"message": "https://unsafe.invalid/value"},
        {"message": "reviewer@example.com"},
        {"message": "/Users/example/private"},
        {"message": "Authorization: Bearer raw-token-value"},
        {"message": "raw report contents"},
        {"message": "The audit is production-ready"},
        {"message": "Security certified"},
    ),
)
def test_validator_blocks_private_material_and_claims(unsafe):
    with pytest.raises(AuthBoundaryAuditBlockedError):
        validate_auth_boundary_audit_report_safe(unsafe)


def test_renderers_are_sanitized_and_csv_is_formula_safe():
    report = build_auth_boundary_audit_report(_settings())
    report.routes[0].path = "=FORMULA_PLACEHOLDER"
    csv_text = render_route_permission_matrix_csv(report)
    assert "'=FORMULA_PLACEHOLDER" in csv_text
    rendered = "\n".join(
        (
            render_auth_boundary_map_markdown(report),
            render_permission_boundary_checklist(report),
            csv_text,
        )
    )
    assert "No live permission" in rendered
    validate_auth_boundary_audit_report_safe(rendered)


def test_artifact_path_traversal_and_unapproved_roots_are_blocked():
    report = build_auth_boundary_audit_report(_settings())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-auth-output")):
        with pytest.raises(AuthBoundaryAuditBlockedError):
            write_auth_boundary_audit_artifacts(report, path)


def test_temp_artifacts_are_complete_and_safe():
    report = build_auth_boundary_audit_report(_settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-auth-boundary-", dir="/tmp") as directory:
        result = write_auth_boundary_audit_artifacts(report, Path(directory))
        assert set(result.files) == set(ARTIFACT_FILES)
        for name in result.files:
            validate_auth_boundary_audit_report_safe(
                (Path(directory) / name).read_text(encoding="utf-8")
            )


def test_cli_and_make_targets_run():
    commands = (
        [".venv/bin/python", "scripts/run_auth_boundary_audit.py"],
        [".venv/bin/python", "scripts/print_auth_boundary_map.py"],
        [".venv/bin/python", "scripts/print_permission_boundary_checklist.py"],
        [
            ".venv/bin/python",
            "scripts/generate_auth_boundary_audit_artifacts.py",
            "--temporary",
        ],
        ["make", "auth-boundary-audit"],
        ["make", "auth-boundary-map"],
        ["make", "permission-boundary-checklist"],
        ["make", "auth-boundary-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_ignore_and_quality_contracts():
    required = (
        "docs/auth-permission-boundary-audit.md",
        "docs/auth-boundary-map.md",
        "docs/permission-boundary-checklist.md",
        "examples/auth-boundary-audit/README.md",
        "examples/auth-boundary-audit/example_auth_boundary_map.md",
        "examples/auth-boundary-audit/example_permission_boundary_checklist.md",
        "examples/auth-boundary-audit/example_route_permission_matrix.csv",
    )
    assert all((ROOT / path).is_file() for path in required)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(pattern in gitignore for pattern in IGNORED_OUTPUTS)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert (
        "quality: auth-boundary-audit auth-boundary-map permission-boundary-checklist" in makefile
    )
    quality = "\n".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "auth-boundary-artifact-check" not in quality
    combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in required)
    assert "AUTH_BOUNDARY_PLACEHOLDER" in combined


def test_public_safety_catches_claims_and_generated_outputs(tmp_path):
    claim = tmp_path / "auth-boundary-map.md"
    assert audit_text(claim, "This auth audit is production-ready.")
    generated = tmp_path / "auth-boundary-audit-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder", encoding="utf-8")
    assert audit_paths([generated])


def test_existing_repository_audits_pass_and_no_route_was_added():
    assert len(application_routes()) == 81
    assert audit_routes() == []

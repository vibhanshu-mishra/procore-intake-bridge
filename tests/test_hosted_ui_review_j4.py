from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.hosted_ui_review import (
    HostedUiModeReadiness,
    HostedUiPageClass,
    HostedUiProtectionType,
    HostedUiSurface,
)
from app.services.hosted_ui_review import (
    ARTIFACT_FILES,
    HostedUiReviewBlockedError,
    build_hosted_ui_page_inventory,
    build_hosted_ui_private_gates,
    build_hosted_ui_readiness_checklist,
    build_hosted_ui_review_report,
    build_hosted_ui_route_matrix,
    collect_hosted_ui_templates,
    render_hosted_ui_route_matrix_csv,
    validate_hosted_ui_review_report_safe,
    write_hosted_ui_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_review_builds_offline_with_safe_complete_inventories():
    report = build_hosted_ui_review_report(settings())
    assert report.pages_total == len(report.pages) > 0
    assert report.routes_total == len(report.routes) > 0
    assert report.page_inventory_complete
    assert report.route_inventory_complete
    assert report.admin_surfaces_protected
    assert report.attachment_surfaces_metadata_only
    assert not report.export_download_routes_present
    assert not report.file_serving_routes_present
    assert not report.external_frontend_assets_present
    assert not report.frontend_build_system_added
    validate_hosted_ui_review_report_safe(report)


def test_page_inventory_covers_every_surface_without_unknowns():
    pages = build_hosted_ui_page_inventory(settings())
    assert set(HostedUiSurface) - {HostedUiSurface.UNKNOWN} <= {item.surface for item in pages}
    assert all(item.page_class is not HostedUiPageClass.UNKNOWN for item in pages)
    assert all(item.protection_type is not HostedUiProtectionType.UNKNOWN for item in pages)
    assert all(item.mode_readiness is not HostedUiModeReadiness.UNKNOWN for item in pages)
    assert collect_hosted_ui_templates(settings())


def test_route_matrix_covers_current_hosted_ui_route_families():
    routes = build_hosted_ui_route_matrix(settings())
    assert routes
    for prefix in ("/admin", "/dashboard", "/review", "/deployment"):
        assert any(item.path.startswith(prefix) for item in routes)
    assert all(item.surface is not HostedUiSurface.UNKNOWN for item in routes)
    assert all(item.page_class is not HostedUiPageClass.UNKNOWN for item in routes)
    assert all(item.protection_type is not HostedUiProtectionType.UNKNOWN for item in routes)


def test_dashboard_admin_review_and_triage_surfaces_are_classified():
    routes = build_hosted_ui_route_matrix(settings())
    surfaces = {item.surface for item in routes}
    assert {
        HostedUiSurface.PRODUCT_DASHBOARD,
        HostedUiSurface.ADMIN_DASHBOARD,
        HostedUiSurface.REVIEW_WORKSPACE,
        HostedUiSurface.TRIAGE_QUEUE,
    } <= surfaces
    protected = [
        item
        for item in routes
        if item.surface
        in {
            HostedUiSurface.PRODUCT_DASHBOARD,
            HostedUiSurface.ADMIN_DASHBOARD,
            HostedUiSurface.REVIEW_WORKSPACE,
            HostedUiSurface.TRIAGE_QUEUE,
        }
    ]
    assert all(item.admin_protected for item in protected)


def test_lifecycle_attachment_and_export_boundaries_are_preserved():
    report = build_hosted_ui_review_report(settings())
    lifecycle = [
        item for item in report.routes if item.surface is HostedUiSurface.LIFECYCLE_CONTROLS
    ]
    attachments = [
        item for item in report.routes if item.surface is HostedUiSurface.ATTACHMENT_METADATA
    ]
    exports = [item for item in report.pages if item.surface is HostedUiSurface.EXPORT_GUIDANCE]
    assert lifecycle and all(item.admin_protected and item.local_only for item in lifecycle)
    assert attachments and all(item.metadata_only and not item.file_serving for item in attachments)
    assert exports and all(item.command_guidance_only for item in exports)


def test_private_gates_and_checklist_are_honest():
    gates = build_hosted_ui_private_gates(settings())
    checklist = build_hosted_ui_readiness_checklist(settings())
    assert gates and all(item.required_for_hosted_evaluation for item in gates)
    assert all(not item.public_repo_resolved for item in gates)
    assert checklist and any(item.private_review_required for item in checklist)


def test_live_and_private_flags_remain_false():
    report = build_hosted_ui_review_report(settings())
    false_flags = (
        "hosted_deployment_attempted",
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "db_external_connection_attempted",
        "scanner_attempted",
        "private_report_contents_exposed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
        "production_approval_claimed",
        "release_approval_claimed",
        "pilot_approval_claimed",
        "deployment_approval_claimed",
    )
    assert not any(getattr(report, field) for field in false_flags)


@pytest.mark.parametrize(
    "key",
    (
        "hosted_ui_require_route_inventory",
        "hosted_ui_require_page_inventory",
        "hosted_ui_require_admin_protection",
        "hosted_ui_require_demo_safe_labels",
        "hosted_ui_require_metadata_only_attachments",
        "hosted_ui_require_no_file_serving",
        "hosted_ui_require_no_export_downloads",
        "hosted_ui_require_no_external_frontend_assets",
        "hosted_ui_require_private_review_gates",
    ),
)
def test_required_controls_fail_closed(key):
    with pytest.raises(HostedUiReviewBlockedError):
        build_hosted_ui_review_report(settings(**{key: False}))


def test_validator_rejects_unsafe_report_flags():
    report = build_hosted_ui_review_report(settings())
    for field in (
        "file_serving_routes_present",
        "export_download_routes_present",
        "external_frontend_assets_present",
        "frontend_build_system_added",
        "hosted_deployment_attempted",
        "external_call_attempted",
        "procore_call_attempted",
        "secrets_exposed",
        "production_approval_claimed",
        "deployment_approval_claimed",
    ):
        with pytest.raises(HostedUiReviewBlockedError):
            validate_hosted_ui_review_report_safe(report.model_copy(update={field: True}))


def test_artifact_generation_is_safe_and_traversal_is_blocked():
    report = build_hosted_ui_review_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-hosted-ui-", dir="/tmp") as root:
        result = write_hosted_ui_review_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        assert not result.hosted_deployment
        assert not result.frontend_build
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(HostedUiReviewBlockedError):
            write_hosted_ui_review_artifacts(report, path)


def test_route_matrix_csv_neutralizes_formula_injection():
    report = build_hosted_ui_review_report(settings())
    report.routes[0].purpose = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_hosted_ui_route_matrix_csv(report)


def test_cli_and_make_targets_run_without_persistent_writes():
    commands = (
        (".venv/bin/python", "scripts/run_hosted_ui_review.py"),
        (".venv/bin/python", "scripts/print_hosted_ui_page_inventory.py"),
        (".venv/bin/python", "scripts/print_hosted_ui_readiness_checklist.py"),
        (".venv/bin/python", "scripts/print_hosted_ui_private_gates.py"),
        (".venv/bin/python", "scripts/generate_hosted_ui_review_artifacts.py", "--temporary"),
        ("make", "hosted-ui-review"),
        ("make", "hosted-ui-page-inventory"),
        ("make", "hosted-ui-readiness-checklist"),
        ("make", "hosted-ui-private-gates"),
        ("make", "hosted-ui-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_navigation_and_quality_contract():
    docs = {
        ROOT / "docs/hosted-ui-preparation.md",
        ROOT / "docs/hosted-ui-page-inventory.md",
        ROOT / "docs/hosted-ui-readiness-checklist.md",
        ROOT / "docs/hosted-ui-private-gates.md",
    }
    assert all(path.is_file() for path in docs)
    canonical = "\n".join(path.read_text().casefold() for path in docs)
    for phrase in ("no hosted deployment", "no external", "no frontend", "production approval"):
        assert phrase in canonical
    examples = list((ROOT / "examples/hosted-ui-review").iterdir())
    assert "PLACEHOLDER" in "\n".join(path.read_text() for path in examples if path.is_file())
    assert not audit_paths(examples)
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]
    quality = " ".join(
        line for line in (ROOT / "Makefile").read_text().splitlines() if line.startswith("quality:")
    )
    for target in (
        "hosted-ui-review",
        "hosted-ui-page-inventory",
        "hosted-ui-readiness-checklist",
        "hosted-ui-private-gates",
    ):
        assert target in quality
    assert "hosted-ui-artifact-check" not in quality


def test_public_safety_blocks_j4_outputs_assets_build_files_and_claims(tmp_path):
    guide = tmp_path / "hosted-ui-preparation.md"
    assert audit_text(guide, '<script src="https://assets.invalid/app.js"></script>')
    assert audit_text(guide, "github_token=private-value")
    assert audit_text(guide, "Hosted UI is deployed and production-ready.")
    assert not audit_text(guide, "No hosted deployment is performed; production is not approved.")
    template = tmp_path / "app" / "templates" / "unsafe.html"
    template.parent.mkdir(parents=True)
    assert audit_text(template, '<link href="//cdn.invalid/ui.css" rel="stylesheet">')
    generated = tmp_path / "hosted-ui-review-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    package = tmp_path / "package.json"
    package.write_text("{}")
    assert audit_paths([generated])
    assert audit_paths([package])


def test_routes_and_workflows_are_unchanged_and_safe():
    assert len(application_routes()) == 81
    assert audit_routes() == []
    workflow_dir = ROOT / ".github/workflows"
    assert not workflow_dir.is_dir() or not any(
        "hosted-ui" in path.name.casefold() for path in workflow_dir.iterdir()
    )

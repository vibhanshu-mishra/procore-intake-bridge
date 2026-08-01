from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.docs_site_polish import DocsAudiencePath, DocsNavigationGroup, DocsPageClass
from app.services.docs_site_polish import (
    ARTIFACT_FILES,
    DocsSitePolishBlockedError,
    build_docs_audience_paths,
    build_docs_link_inventory,
    build_docs_navigation_groups,
    build_docs_navigation_map,
    build_docs_site_checklist,
    build_docs_site_polish_report,
    collect_docs_pages,
    collect_mkdocs_nav,
    render_docs_link_inventory_csv,
    validate_docs_site_polish_report_safe,
    write_docs_site_polish_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_with_complete_local_site_contract():
    report = build_docs_site_polish_report(settings())
    assert report.local_only
    assert report.docs_total == len(report.pages) > 0
    assert report.nav_groups_total == len(DocsNavigationGroup)
    assert report.audience_paths_total == len(DocsAudiencePath)
    assert report.checklist_items_total == len(report.checklist) > 0
    assert report.mkdocs_config_present
    assert report.nav_structure_present
    assert report.reader_paths_present
    assert report.local_preview_documented
    validate_docs_site_polish_report_safe(report)


def test_every_expected_audience_path_is_present_and_local_only():
    paths = build_docs_audience_paths(settings())
    assert {item.audience for item in paths} == set(DocsAudiencePath)
    assert all(item.local_only and item.documents for item in paths)
    assert all(
        all(not document.startswith(("http://", "https://")) for document in item.documents)
        for item in paths
    )


def test_every_navigation_group_has_existing_entries():
    groups = build_docs_navigation_groups(settings())
    navigation = build_docs_navigation_map(settings())
    assert set(groups) == set(DocsNavigationGroup)
    represented = {item.group for item in navigation} | {
        item.navigation_group for item in collect_docs_pages(settings()) if item.in_mkdocs_nav
    }
    assert represented == set(DocsNavigationGroup)
    assert all(item.target_exists for item in navigation)
    assert all(item.page_class is not DocsPageClass.UNKNOWN for item in navigation)
    assert collect_mkdocs_nav(settings())


def test_core_j1_through_j4_security_and_product_docs_are_discoverable():
    pages = {item.path: item for item in collect_docs_pages(settings())}
    required = {
        "index.md",
        "docs-navigation.md",
        "local-installer-guide.md",
        "demo-data-seed-reset.md",
        "api-route-reference.md",
        "hosted-ui-preparation.md",
        "security-threat-model.md",
        "security-gap-closeout.md",
        "final-security-readiness-review.md",
        "intake-review-workspace.md",
        "intake-lifecycle-status-flow.md",
        "operator-triage-queue.md",
        "attachment-review-manifest-ux.md",
        "operator-export-pack.md",
        "product-dashboard.md",
        "demo-product-walkthrough.md",
    }
    assert required <= set(pages)
    nav_required = required - {"docs-navigation.md"}
    assert all(pages[path].in_mkdocs_nav for path in nav_required)


def test_link_inventory_and_checklist_are_local_and_complete():
    links = build_docs_link_inventory(settings())
    checklist = build_docs_site_checklist(settings())
    assert links
    assert all(not item.internal or item.target_exists or item.anchor_only for item in links)
    assert checklist and all(item.passed for item in checklist if item.blocker)


def test_no_hosting_external_or_live_operation_flags_are_set():
    report = build_docs_site_polish_report(settings())
    false_flags = (
        "hosting_automation_present",
        "external_analytics_present",
        "external_assets_present",
        "docs_deploy_attempted",
        "external_call_attempted",
        "github_api_attempted",
        "package_build_attempted",
        "release_attempted",
        "deploy_attempted",
        "workflow_changed",
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
        "docs_site_polish_require_local_only",
        "docs_site_polish_require_nav_groups",
        "docs_site_polish_require_reader_paths",
        "docs_site_polish_require_no_hosting_automation",
        "docs_site_polish_require_no_external_analytics",
        "docs_site_polish_require_no_external_assets",
        "docs_site_polish_require_generated_output_ignores",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(DocsSitePolishBlockedError):
        build_docs_site_polish_report(settings(**{key: False}))


def test_validator_rejects_unsafe_flags():
    report = build_docs_site_polish_report(settings())
    for field in (
        "hosting_automation_present",
        "external_analytics_present",
        "external_assets_present",
        "docs_deploy_attempted",
        "external_call_attempted",
        "github_api_attempted",
        "package_build_attempted",
        "release_attempted",
        "deploy_attempted",
        "workflow_changed",
        "secrets_exposed",
        "production_approval_claimed",
        "deployment_approval_claimed",
    ):
        with pytest.raises(DocsSitePolishBlockedError):
            validate_docs_site_polish_report_safe(report.model_copy(update={field: True}))


def test_artifacts_are_safe_and_path_traversal_is_blocked():
    report = build_docs_site_polish_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-docs-site-polish-", dir="/tmp") as root:
        result = write_docs_site_polish_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        assert not result.docs_deployment
        assert not result.external_operations
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(DocsSitePolishBlockedError):
            write_docs_site_polish_artifacts(report, path)


def test_link_inventory_csv_neutralizes_formula_injection():
    report = build_docs_site_polish_report(settings())
    report.link_inventory[0].label = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_docs_link_inventory_csv(report)


def test_cli_and_make_targets_run_without_persistent_output():
    commands = (
        (".venv/bin/python", "scripts/run_docs_site_polish_review.py"),
        (".venv/bin/python", "scripts/print_docs_reader_paths.py"),
        (".venv/bin/python", "scripts/print_docs_navigation_map.py"),
        (".venv/bin/python", "scripts/print_docs_site_checklist.py"),
        (".venv/bin/python", "scripts/generate_docs_site_polish_artifacts.py", "--temporary"),
        ("make", "docs-site-polish-review"),
        ("make", "docs-reader-paths"),
        ("make", "docs-navigation-map"),
        ("make", "docs-site-checklist"),
        ("make", "docs-site-polish-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_navigation_and_quality_contract():
    docs = {
        ROOT / "docs/docs-site-polish.md",
        ROOT / "docs/docs-reader-paths.md",
        ROOT / "docs/docs-navigation-map.md",
    }
    assert all(path.is_file() for path in docs)
    canonical = "\n".join(path.read_text().casefold() for path in docs)
    for phrase in ("local-only", "no docs deployment", "no external", "production approval"):
        assert phrase in canonical
    examples = list((ROOT / "examples/docs-site-polish").iterdir())
    assert "PLACEHOLDER" in "\n".join(path.read_text() for path in examples if path.is_file())
    assert not audit_paths(examples)
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]
    quality = " ".join(
        line for line in (ROOT / "Makefile").read_text().splitlines() if line.startswith("quality:")
    )
    for target in (
        "docs-site-polish-review",
        "docs-reader-paths",
        "docs-navigation-map",
        "docs-site-checklist",
    ):
        assert target in quality
    assert "docs-site-polish-artifact-check" not in quality


def test_public_safety_blocks_outputs_external_services_private_values_and_claims(tmp_path):
    guide = tmp_path / "docs-site-polish.md"
    assert audit_text(guide, '<script src="https://analytics.invalid/site.js"></script>')
    assert audit_text(guide, "github_token=private-value")
    assert audit_text(guide, "The docs site is deployed and production-ready.")
    assert not audit_text(guide, "No docs deployment occurs; production is not approved.")
    generated = tmp_path / "docs-site-polish-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    assert audit_paths([generated])


def test_routes_and_workflows_remain_unchanged():
    assert len(application_routes()) == 81
    assert audit_routes() == []
    workflow_dir = ROOT / ".github/workflows"
    assert not workflow_dir.is_dir() or not any(
        "docs" in path.name.casefold() and "deploy" in path.read_text().casefold()
        for path in workflow_dir.iterdir()
    )

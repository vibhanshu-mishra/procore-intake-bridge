from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.api_docs_review import (
    ApiMethodRisk,
    ApiProtectionType,
    ApiRouteClass,
)
from app.services.api_docs_review import (
    ARTIFACT_FILES,
    ApiDocsReviewBlockedError,
    build_api_docs_report,
    build_api_route_reference,
    build_api_usage_examples,
    render_api_route_matrix_csv,
    render_openapi_local_guide_markdown,
    validate_api_docs_report_safe,
    write_api_docs_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_route_reference_documents_the_complete_local_route_table():
    routes = build_api_route_reference(settings())
    assert len(application_routes()) == 81
    assert len(routes) == 81
    assert all(item.route_class is not ApiRouteClass.UNKNOWN for item in routes)
    assert all(item.protection_type is not ApiProtectionType.UNKNOWN for item in routes)
    assert all(item.method_risk is not ApiMethodRisk.UNKNOWN for item in routes)


def test_public_health_and_readiness_routes_are_intentionally_public_gets():
    routes = build_api_route_reference(settings())
    public = {item.path: item for item in routes if item.path in {"/health", "/ready", "/safety"}}
    assert set(public) == {"/health", "/ready", "/safety"}
    assert all(item.method == "GET" for item in public.values())
    assert all(
        item.protection_type is ApiProtectionType.INTENTIONALLY_PUBLIC for item in public.values()
    )


def test_protected_route_families_have_known_boundaries():
    routes = build_api_route_reference(settings())
    protected = [
        item
        for item in routes
        if item.path.startswith(("/admin", "/dashboard", "/review", "/deployment"))
    ]
    assert protected
    assert all(not item.intentionally_public for item in protected)
    assert all(item.protection_type is not ApiProtectionType.UNKNOWN for item in protected)


def test_lifecycle_and_webhook_posts_have_their_exact_boundaries():
    routes = build_api_route_reference(settings())
    lifecycle = [
        item
        for item in routes
        if item.method == "POST" and item.path.endswith("/{record_id}/lifecycle")
    ]
    webhook = [
        item for item in routes if item.path in {"/webhooks/procore", "/webhooks/procore/dry-run"}
    ]
    assert len(lifecycle) == 2
    assert all(item.route_class is ApiRouteClass.LIFECYCLE_LOCAL_MUTATION for item in lifecycle)
    assert all(item.method_risk is ApiMethodRisk.LOCAL_ONLY_POST for item in lifecycle)
    assert len(webhook) == 2
    assert all(item.route_class is ApiRouteClass.WEBHOOK_SIGNATURE_BOUNDARY for item in webhook)
    assert all(
        item.protection_type is ApiProtectionType.WEBHOOK_SIGNATURE_REQUIRED for item in webhook
    )


def test_report_is_complete_safe_and_offline():
    report = build_api_docs_report(settings())
    assert report.routes_total == report.documented_routes_total == 81
    assert report.undocumented_routes_total == report.unsafe_routes_total == 0
    assert report.all_routes_documented
    assert report.no_export_download_routes
    assert report.no_file_serving_routes
    assert report.no_procore_write_routes
    assert report.demo_examples_safe
    false_flags = (
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "db_external_connection_attempted",
        "scanner_attempted",
        "openapi_external_tool_attempted",
        "private_report_contents_exposed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
        "production_approval_claimed",
        "release_approval_claimed",
        "pilot_approval_claimed",
    )
    assert not any(getattr(report, name) for name in false_flags)
    validate_api_docs_report_safe(report)


def test_usage_examples_and_openapi_guide_are_demo_safe():
    examples = build_api_usage_examples(settings())
    assert examples
    assert all(item.local_only and item.fake_data_only and not item.live_call for item in examples)
    guide = render_openapi_local_guide_markdown(build_api_docs_report(settings())).casefold()
    for phrase in ("locally", "does not start", "external openapi tooling", "does not approve"):
        assert phrase in guide


@pytest.mark.parametrize(
    "key",
    (
        "api_docs_require_route_reference",
        "api_docs_require_auth_boundary",
        "api_docs_require_demo_safe_examples",
        "api_docs_require_no_private_data",
        "api_docs_require_no_file_serving",
        "api_docs_require_no_export_downloads",
        "api_docs_require_no_procore_writes",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(ApiDocsReviewBlockedError):
        build_api_docs_report(settings(**{key: False}))


def test_validator_rejects_unsafe_flags():
    report = build_api_docs_report(settings())
    for field in (
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "db_external_connection_attempted",
        "scanner_attempted",
        "openapi_external_tool_attempted",
        "private_report_contents_exposed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
        "production_approval_claimed",
        "release_approval_claimed",
        "pilot_approval_claimed",
    ):
        with pytest.raises(ApiDocsReviewBlockedError):
            validate_api_docs_report_safe(report.model_copy(update={field: True}))


def test_artifacts_are_sanitized_and_traversal_is_blocked():
    report = build_api_docs_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-api-docs-", dir="/tmp") as root:
        result = write_api_docs_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        assert not result.external_operations
        assert not audit_paths([Path(root) / name for name in result.files])
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(ApiDocsReviewBlockedError):
            write_api_docs_artifacts(report, path)


def test_csv_formula_injection_is_neutralized():
    report = build_api_docs_report(settings())
    report.routes[0].purpose = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_api_route_matrix_csv(report)


def test_cli_and_make_targets_run_without_persistent_writes():
    commands = (
        (".venv/bin/python", "scripts/run_api_docs_review.py"),
        (".venv/bin/python", "scripts/print_api_route_reference.py"),
        (".venv/bin/python", "scripts/print_api_usage_examples.py"),
        (".venv/bin/python", "scripts/print_openapi_local_guide.py"),
        (".venv/bin/python", "scripts/generate_api_docs_artifacts.py", "--temporary"),
        ("make", "api-docs-review"),
        ("make", "api-route-reference"),
        ("make", "api-usage-examples"),
        ("make", "openapi-local-guide"),
        ("make", "api-docs-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_navigation_and_quality_contract():
    docs = {
        ROOT / "docs/api-route-reference.md",
        ROOT / "docs/api-usage-examples.md",
        ROOT / "docs/openapi-local-guide.md",
        ROOT / "docs/api-docs-review.md",
    }
    assert all(path.is_file() for path in docs)
    canonical = "\n".join(path.read_text().casefold() for path in docs)
    for phrase in ("local", "no live api calls", "external openapi tooling", "production approval"):
        assert phrase in canonical
    examples = list((ROOT / "examples/api-docs-review").iterdir())
    assert "PLACEHOLDER" in "\n".join(path.read_text() for path in examples if path.is_file())
    assert not audit_paths(examples)
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]
    quality = " ".join(
        line for line in (ROOT / "Makefile").read_text().splitlines() if line.startswith("quality:")
    )
    for target in (
        "api-docs-review",
        "api-route-reference",
        "api-usage-examples",
        "openapi-local-guide",
    ):
        assert target in quality
    assert "api-docs-artifact-check" not in quality


def test_public_safety_and_route_audits_cover_j3_boundaries(tmp_path):
    guide = tmp_path / "api-docs-review.md"
    assert audit_text(guide, "github_token=private-value")
    assert audit_text(guide, "This API reference is production-ready.")
    assert not audit_text(guide, "This does not imply production approval.")
    generated = tmp_path / "api-docs-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    assert audit_paths([generated])
    assert audit_routes() == []


def test_workflows_and_api_route_count_are_unchanged():
    assert len(application_routes()) == 81
    workflow_dir = ROOT / ".github/workflows"
    assert not workflow_dir.is_dir() or not any(
        "api-doc" in path.name.casefold() for path in workflow_dir.iterdir()
    )

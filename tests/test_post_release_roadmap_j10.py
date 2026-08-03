"""Offline contract tests for the J10 post-release roadmap planning pack."""

from pathlib import Path
from subprocess import run
from sys import executable
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.post_release_roadmap import RoadmapDomain
from app.services.post_release_roadmap import (
    ARTIFACT_FILES,
    PostReleaseRoadmapBlockedError,
    build_future_work_backlog,
    build_hosted_pilot_backlog,
    build_known_limitations_register,
    build_post_release_dependencies,
    build_post_release_roadmap_matrix,
    build_post_release_roadmap_report,
    build_pre_tag_reminder_checklist,
    build_private_review_backlog,
    build_product_improvement_backlog,
    build_productionization_backlog,
    build_roadmap_domain_summaries,
    build_security_future_work_register,
    render_post_release_roadmap_matrix_csv,
    validate_post_release_roadmap_report_safe,
    write_post_release_roadmap_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_public_usability import audit_repository
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_with_all_j10_views_and_domains():
    report = build_post_release_roadmap_report(settings())
    assert report.target_version == "0.1.0"
    assert report.status.value == "needs_review"
    assert report.decision.value in {
        "post_release_roadmap_ready_for_maintainer_review",
        "post_release_roadmap_needs_review",
    }
    assert report.public_repo_safe_for_roadmap_review
    assert report.maintainer_decision_required
    assert report.private_review_required
    assert {item.domain for item in report.domain_summaries} == set(RoadmapDomain)
    assert report.known_limitations
    assert report.future_work_backlog
    assert report.private_review_backlog
    assert report.productionization_backlog
    assert report.hosted_pilot_backlog
    assert report.security_future_work
    assert report.product_improvement_backlog
    assert report.pre_tag_reminders
    assert len(report.roadmap_matrix) == len(RoadmapDomain)
    validate_post_release_roadmap_report_safe(report)


def test_j10_dependencies_and_view_builders_are_complete():
    dependencies = build_post_release_dependencies(settings())
    assert dependencies and all(dependencies.values())
    assert build_roadmap_domain_summaries(settings())
    assert build_known_limitations_register(settings())
    assert build_future_work_backlog(settings())
    assert build_private_review_backlog(settings())
    assert build_productionization_backlog(settings())
    assert build_hosted_pilot_backlog(settings())
    assert build_security_future_work_register(settings())
    assert build_product_improvement_backlog(settings())
    assert build_pre_tag_reminder_checklist(settings())
    assert build_post_release_roadmap_matrix(settings())


def test_report_has_no_live_issue_ticket_release_or_approval_flags():
    report = build_post_release_roadmap_report(settings())
    false_flags = (
        "actual_release_performed",
        "package_build_attempted",
        "docker_build_attempted",
        "publish_attempted",
        "tag_attempted",
        "release_attempted",
        "deploy_attempted",
        "docs_deploy_attempted",
        "workflow_changed",
        "github_api_attempted",
        "issue_creation_attempted",
        "ticket_creation_attempted",
        "package_registry_call_attempted",
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "notification_attempted",
        "telemetry_added",
        "production_approval_granted",
        "release_approval_granted",
        "pilot_approval_granted",
        "deployment_approval_granted",
        "compliance_claimed",
        "certification_claimed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
    )
    assert not any(getattr(report, field) for field in false_flags)


@pytest.mark.parametrize(
    "field",
    (
        "issue_creation_attempted",
        "ticket_creation_attempted",
        "compliance_claimed",
        "certification_claimed",
        "actual_release_performed",
        "publish_attempted",
        "tag_attempted",
        "deploy_attempted",
    ),
)
def test_report_validator_rejects_unsafe_j10_flags(field):
    report = build_post_release_roadmap_report(settings()).model_copy(update={field: True})
    with pytest.raises(PostReleaseRoadmapBlockedError):
        validate_post_release_roadmap_report_safe(report)


def test_report_serialization_is_public_safe():
    report = build_post_release_roadmap_report(settings())
    text = report.model_dump_json().casefold()
    for forbidden in (
        "https://",
        "github_token",
        "package_registry_token",
        "database_url",
        "signed_url",
        "private report contents",
        "issue id:",
        "ticket id:",
    ):
        assert forbidden not in text


@pytest.mark.parametrize(
    "key",
    (
        "post_release_roadmap_enabled",
        "post_release_roadmap_fail_closed",
        "post_release_roadmap_require_known_limitations",
        "post_release_roadmap_require_private_review_backlog",
        "post_release_roadmap_require_productionization_backlog",
        "post_release_roadmap_require_hosted_pilot_backlog",
        "post_release_roadmap_require_security_future_work",
        "post_release_roadmap_require_product_backlog",
        "post_release_roadmap_require_pre_tag_reminder",
        "post_release_roadmap_require_no_release_actions",
        "post_release_roadmap_require_no_build",
        "post_release_roadmap_require_no_publish",
        "post_release_roadmap_require_no_tag",
        "post_release_roadmap_require_no_deploy",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(PostReleaseRoadmapBlockedError):
        build_post_release_roadmap_report(settings(**{key: False}))


@pytest.mark.parametrize(
    "key",
    (
        "post_release_roadmap_allow_real_identities",
        "post_release_roadmap_allow_real_domains",
        "post_release_roadmap_allow_real_urls",
        "post_release_roadmap_allow_report_contents",
        "post_release_roadmap_allow_private_paths",
    ),
)
def test_unsafe_material_settings_fail_closed(key):
    with pytest.raises(PostReleaseRoadmapBlockedError):
        build_post_release_roadmap_report(settings(**{key: True}))


def test_artifacts_are_sanitized_and_path_traversal_is_blocked():
    report = build_post_release_roadmap_report(settings())
    with TemporaryDirectory(
        prefix="procore-intake-bridge-post-release-roadmap-", dir="/tmp"
    ) as root:
        result = write_post_release_roadmap_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert result.sanitized
        assert not any(
            (
                result.live_operations,
                result.package_build,
                result.docker_build,
                result.publish,
                result.tag,
                result.release,
                result.deploy,
            )
        )
        assert (Path(root) / "manifest.json").is_file()
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(PostReleaseRoadmapBlockedError):
            write_post_release_roadmap_artifacts(report, path)


def test_roadmap_csv_neutralizes_formula_injection():
    report = build_post_release_roadmap_report(settings())
    report.roadmap_matrix[0].summary = "=FORMULA_PLACEHOLDER"
    csv_text = render_post_release_roadmap_matrix_csv(report)
    assert "'=FORMULA_PLACEHOLDER" in csv_text


def test_public_audits_docs_site_and_routes_pass():
    assert not [item for item in audit_repository(ROOT) if item.level == "FAIL"]
    assert not [item for item in check_docs_site(ROOT) if item.level == "FAIL"]
    assert not audit_paths(
        [
            ROOT / "docs/post-release-roadmap.md",
            ROOT / "docs/known-limitations-register.md",
            ROOT / "docs/future-work-backlog.md",
            ROOT / "docs/private-review-backlog.md",
            ROOT / "docs/pre-tag-reminder-checklist.md",
        ]
    )
    assert not audit_routes()
    assert application_routes()


@pytest.mark.parametrize(
    "script",
    (
        "run_post_release_roadmap.py",
        "print_known_limitations_register.py",
        "print_future_work_backlog.py",
        "print_private_review_backlog.py",
        "print_pre_tag_reminder_checklist.py",
    ),
)
def test_j10_cli_scripts_run_offline(script):
    result = run(
        [executable, f"scripts/{script}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "http://" not in result.stdout and "https://" not in result.stdout
    assert str(ROOT) not in result.stdout


def test_artifact_generator_uses_disposable_temp_output():
    result = run(
        [executable, "scripts/generate_post_release_roadmap_artifacts.py", "--temporary"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"sanitized": true' in result.stdout.casefold()
    assert "https://" not in result.stdout
    assert str(ROOT) not in result.stdout


def test_make_targets_and_quality_exclude_persistent_roadmap_artifacts():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "post-release-roadmap",
        "known-limitations-register",
        "future-work-backlog",
        "private-review-backlog",
        "pre-tag-reminder-checklist",
        "post-release-roadmap-artifact-check",
    ):
        assert f"{target}:" in makefile
    quality = " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "post-release-roadmap-artifact-check" not in quality


@pytest.mark.parametrize(
    "claim",
    (
        "The issue was created and the ticket was closed.",
        "Ticket #123 was created.",
        "The issue/ticket was created.",
        "The package was published and the release was completed.",
        "The package was published.",
        "Package publication completed.",
        "A release happened and a deployment was performed.",
        "Production approved and compliance certified.",
        "Release was approved and deployment approval granted.",
        "The package is production-ready.",
    ),
)
def test_public_safety_blocks_j10_issue_ticket_release_and_approval_claims(tmp_path, claim):
    path = tmp_path / "post-release-roadmap.md"
    path.write_text(claim, encoding="utf-8")
    assert audit_text(path, claim)


def test_public_safety_allows_j10_negations_and_placeholders(tmp_path):
    path = tmp_path / "post-release-roadmap.md"
    text = (
        "No issue or ticket is opened. No release, build, publish, tag, or deployment happened.\n"
        "PRIVATE_REVIEW_REF_PLACEHOLDER and OWNER_PLACEHOLDER remain outside Git.\n"
    )
    path.write_text(text, encoding="utf-8")
    assert not audit_text(path, text)


def test_example_and_workflow_boundaries_are_public_safe():
    examples = sorted((ROOT / "examples/post-release-roadmap").glob("*"))
    assert examples
    for path in examples:
        if path.is_file():
            assert not audit_text(path, path.read_text(encoding="utf-8"))
    workflow_dir = ROOT / ".github/workflows"
    if workflow_dir.is_dir():
        for path in workflow_dir.glob("*"):
            text = path.read_text(encoding="utf-8").casefold()
            assert "gh-pages" not in text
            assert "pages deploy" not in text

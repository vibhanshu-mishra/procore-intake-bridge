"""Offline contract tests for the J8 versioned release handoff."""

from pathlib import Path
from subprocess import run
from sys import executable
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.versioned_release_handoff import VersionedReleaseDomain
from app.services.versioned_release_handoff import (
    ARTIFACT_FILES,
    VersionedReleaseHandoffBlockedError,
    build_known_limitations_summary,
    build_maintainer_release_decision_checklist,
    build_post_release_checklist,
    build_release_evidence_matrix,
    build_release_notes_draft,
    build_release_scope_summary,
    build_versioned_release_dependencies,
    build_versioned_release_domain_summaries,
    build_versioned_release_gates,
    build_versioned_release_handoff_report,
    render_release_evidence_matrix_csv,
    validate_versioned_release_handoff_report_safe,
    write_versioned_release_handoff_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_public_usability import audit_repository
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_for_target_version_and_all_domains():
    report = build_versioned_release_handoff_report(settings())
    assert report.target_version == "0.1.0"
    assert report.domains_total == len(VersionedReleaseDomain) == 15
    assert {item.domain for item in report.domain_summaries} == set(VersionedReleaseDomain)
    assert report.gates_total == len(report.gates) > 0
    assert report.public_repo_safe_for_release_handoff
    assert report.maintainer_authorization_required
    assert report.private_review_required
    validate_versioned_release_handoff_report_safe(report)


def test_dependencies_cover_release_candidate_and_public_surfaces():
    dependencies = build_versioned_release_dependencies(settings())
    assert dependencies and all(dependencies.values())
    joined = " ".join(dependencies).casefold()
    for term in (
        "candidate",
        "version",
        "package",
        "setup",
        "demo",
        "api",
        "hosted",
        "docs",
        "security",
    ):
        assert term in joined


def test_domains_gates_and_release_material_are_complete():
    summaries = build_versioned_release_domain_summaries(settings())
    gates = build_versioned_release_gates(settings())
    assert {item.domain for item in summaries} == set(VersionedReleaseDomain)
    assert all(item.public_safe for item in summaries)
    assert gates and all(
        getattr(item.status, "value", item.status) not in {"blocked", "missing"}
        for item in gates
    )
    assert build_release_notes_draft(settings())
    assert build_release_scope_summary(settings())
    limitations = build_known_limitations_summary(settings())
    limitation_text = " ".join(
        f"{item.title} {item.summary}" for item in limitations
    ).casefold()
    for term in (
        "private review",
        "production approval",
        "hosted deployment",
        "notification",
        "full audit log",
        "retention enforcement",
        "app-level encryption",
        "privacy",
        "legal compliance claim",
    ):
        assert term in limitation_text
    assert build_maintainer_release_decision_checklist(settings())
    assert build_post_release_checklist(settings())
    assert build_release_evidence_matrix(settings())


def test_no_live_operations_or_approval_flags_are_set():
    report = build_versioned_release_handoff_report(settings())
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
        "package_registry_call_attempted",
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "db_external_connection_attempted",
        "scanner_attempted",
        "production_approval_granted",
        "release_approval_granted",
        "pilot_approval_granted",
        "deployment_approval_granted",
        "package_publication_claimed",
        "docs_hosting_claimed",
        "private_report_contents_exposed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
    )
    assert not any(getattr(report, field) for field in false_flags)


def test_report_serialization_contains_no_private_or_approval_material():
    report = build_versioned_release_handoff_report(settings())
    text = report.model_dump_json().casefold()
    for forbidden in (
        "github_token",
        "package_registry_token",
        "signing_key",
        "database_url",
        "signed_url",
        "storage_key",
        "https://",
        "production approval granted",
        "release approval granted",
        "docs hosting claimed",
    ):
        assert forbidden not in text


@pytest.mark.parametrize(
    "key",
    (
        "versioned_release_handoff_require_rc_review",
        "versioned_release_handoff_require_release_notes_draft",
        "versioned_release_handoff_require_included_scope",
        "versioned_release_handoff_require_known_limitations",
        "versioned_release_handoff_require_maintainer_decision",
        "versioned_release_handoff_require_no_build",
        "versioned_release_handoff_require_no_publish",
        "versioned_release_handoff_require_no_tag",
        "versioned_release_handoff_require_no_release",
        "versioned_release_handoff_require_no_deploy",
        "versioned_release_handoff_require_no_workflow_changes",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(VersionedReleaseHandoffBlockedError):
        build_versioned_release_handoff_report(settings(**{key: False}))


def test_artifacts_are_safe_and_path_traversal_is_blocked():
    report = build_versioned_release_handoff_report(settings())
    with TemporaryDirectory(
        prefix="procore-intake-bridge-versioned-release-handoff-",
        dir="/tmp",
    ) as root:
        result = write_versioned_release_handoff_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
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
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(VersionedReleaseHandoffBlockedError):
            write_versioned_release_handoff_artifacts(report, path)


def test_release_evidence_csv_neutralizes_formula_injection():
    report = build_versioned_release_handoff_report(settings())
    report.release_evidence_matrix[0].evidence = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_release_evidence_matrix_csv(report)


def test_public_audits_and_routes_pass():
    assert not [item for item in audit_repository(ROOT) if item.level == "FAIL"]
    assert not [item for item in check_docs_site(ROOT) if item.level == "FAIL"]
    assert not audit_paths([ROOT / "README.md"])
    assert not audit_routes()
    assert application_routes()


@pytest.mark.parametrize(
    "script",
    (
        "run_versioned_release_handoff.py",
        "print_release_notes_draft.py",
        "print_release_scope_summary.py",
        "print_maintainer_release_decision_checklist.py",
        "print_post_release_checklist.py",
    ),
)
def test_cli_scripts_run_offline(script):
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


def test_artifact_generator_writes_temp_output_safely():
    with TemporaryDirectory(
        prefix="procore-intake-bridge-versioned-release-", dir="/tmp"
    ) as root:
        result = run(
            [
                executable,
                "scripts/generate_versioned_release_handoff_artifacts.py",
                "--output-root",
                root,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert (Path(root) / "manifest.json").is_file()


def test_public_safety_blocks_j8_private_material_and_live_claims(tmp_path):
    private = tmp_path / "versioned-release-handoff.md"
    private.write_text("package_registry_token = real-secret\n", encoding="utf-8")
    assert audit_text(private, private.read_text())
    claim = tmp_path / "release-notes-draft.md"
    claim.write_text("The package was published and the release was created.\n", encoding="utf-8")
    assert audit_text(claim, claim.read_text())


@pytest.mark.parametrize(
    "claim",
    (
        "Actual release performed.",
        "Package publication completed.",
        "Docs hosting is live.",
        "Release approval granted.",
    ),
)
def test_public_safety_blocks_additional_j8_claims(tmp_path, claim):
    path = tmp_path / "versioned-release-handoff.md"
    path.write_text(claim, encoding="utf-8")
    assert audit_text(path, claim)

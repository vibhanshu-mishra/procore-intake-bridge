"""Offline contract tests for the J9 public maintainer handoff."""

from pathlib import Path
from subprocess import run
from sys import executable
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.maintainer_handoff import (
    MaintainerHandoffDomain,
)
from app.services.maintainer_handoff import (
    ARTIFACT_FILES,
    MaintainerHandoffBlockedError,
    build_maintainer_command_plan,
    build_maintainer_handoff_dependencies,
    build_maintainer_handoff_report,
    render_maintainer_handoff_matrix_csv,
    validate_maintainer_handoff_report_safe,
    write_maintainer_handoff_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_public_usability import audit_repository
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_for_prepared_version_and_all_domains():
    report = build_maintainer_handoff_report(settings())
    assert report.target_version == "0.1.0"
    assert report.domains_total == len(MaintainerHandoffDomain) == 14
    assert {item.domain for item in report.domain_summaries} == set(MaintainerHandoffDomain)
    assert report.gates_total == len(report.gates) > 0
    assert report.public_repo_safe_for_handoff
    assert report.maintainer_decision_required
    assert report.private_review_required
    validate_maintainer_handoff_report_safe(report)


def test_dependencies_and_command_plan_are_complete_and_non_operational():
    dependencies = build_maintainer_handoff_dependencies(settings())
    assert dependencies and all(dependencies.values())
    plan = build_maintainer_command_plan(settings())
    assert plan
    assert all(item.safe_read_only for item in plan)
    assert not any(
        item.live_operation or item.external_operation or item.database_access
        for item in plan
    )
    assert not any(
        item.command.casefold().startswith(("make publish", "make deploy", "git tag"))
        for item in plan
    )


def test_report_has_no_live_operation_or_approval_flags():
    report = build_maintainer_handoff_report(settings())
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
        "production_approval_granted",
        "release_approval_granted",
        "pilot_approval_granted",
        "deployment_approval_granted",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
    )
    assert not any(getattr(report, field) for field in false_flags)


def test_report_serialization_is_public_safe():
    report = build_maintainer_handoff_report(settings())
    text = report.model_dump_json().casefold()
    for forbidden in (
        "https://",
        "github_token",
        "package_registry_token",
        "database_url",
        "signed_url",
        "private report contents",
    ):
        assert forbidden not in text


@pytest.mark.parametrize(
    "key",
    (
        "maintainer_handoff_enabled",
        "maintainer_handoff_fail_closed",
        "maintainer_handoff_require_release_handoff",
        "maintainer_handoff_require_safe_command_plan",
        "maintainer_handoff_require_private_review_boundary",
        "maintainer_handoff_require_no_release_actions",
        "maintainer_handoff_require_no_build",
        "maintainer_handoff_require_no_publish",
        "maintainer_handoff_require_no_tag",
        "maintainer_handoff_require_no_deploy",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(MaintainerHandoffBlockedError):
        build_maintainer_handoff_report(settings(**{key: False}))


@pytest.mark.parametrize(
    "key",
    (
        "maintainer_handoff_allow_real_identities",
        "maintainer_handoff_allow_real_domains",
        "maintainer_handoff_allow_real_urls",
        "maintainer_handoff_allow_report_contents",
        "maintainer_handoff_allow_private_paths",
    ),
)
def test_unsafe_material_settings_fail_closed(key):
    with pytest.raises(MaintainerHandoffBlockedError):
        build_maintainer_handoff_report(settings(**{key: True}))


def test_artifacts_are_sanitized_and_path_traversal_is_blocked():
    report = build_maintainer_handoff_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-maintainer-handoff-", dir="/tmp") as root:
        result = write_maintainer_handoff_artifacts(report, Path(root))
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
        assert (Path(root) / "manifest.json").is_file()
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(MaintainerHandoffBlockedError):
            write_maintainer_handoff_artifacts(report, path)


def test_handoff_matrix_csv_neutralizes_formula_injection():
    report = build_maintainer_handoff_report(settings())
    report.handoff_matrix[0].evidence = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_maintainer_handoff_matrix_csv(report)


def test_public_audits_and_docs_site_pass():
    assert not [item for item in audit_repository(ROOT) if item.level == "FAIL"]
    assert not [item for item in check_docs_site(ROOT) if item.level == "FAIL"]
    assert not audit_paths([ROOT / "docs/maintainer-handoff.md"])


@pytest.mark.parametrize(
    "script",
    (
        "run_maintainer_handoff.py",
        "print_maintainer_quickstart.py",
        "print_maintainer_review_checklist.py",
        "print_maintainer_command_plan.py",
        "print_maintainer_decision_log_template.py",
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


def test_artifact_generator_uses_disposable_temp_output():
    result = run(
        [executable, "scripts/generate_maintainer_handoff_artifacts.py", "--temporary"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"sanitized": true' in result.stdout.casefold()
    assert "https://" not in result.stdout


def test_public_safety_blocks_j9_private_material_and_live_claims(tmp_path):
    private = tmp_path / "maintainer-handoff.md"
    private.write_text("package_registry_token = real-secret\n", encoding="utf-8")
    assert audit_text(private, private.read_text(encoding="utf-8"))

    claim = tmp_path / "maintainer-command-plan.md"
    claim.write_text("The production approved.\n", encoding="utf-8")
    assert audit_text(claim, claim.read_text(encoding="utf-8"))

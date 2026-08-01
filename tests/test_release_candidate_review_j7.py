from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest
from app.services.release_candidate_review import (
    ARTIFACT_FILES,
    ReleaseCandidateReviewBlockedError,
    build_release_candidate_command_plan,
    build_release_candidate_dependencies,
    build_release_candidate_domain_summaries,
    build_release_candidate_gap_register,
    build_release_candidate_gates,
    build_release_candidate_matrix,
    build_release_candidate_report,
    render_release_candidate_matrix_csv,
    validate_release_candidate_report_safe,
    write_release_candidate_artifacts,
)

from app.config import Settings
from app.schemas.release_candidate_review import (
    ReleaseCandidateDomain,
    ReleaseCandidateGateStatus,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_for_target_version_and_all_domains():
    report = build_release_candidate_report(settings())
    assert report.target_version == "0.1.0"
    assert report.domains_total == len(ReleaseCandidateDomain) == 15
    assert {item.domain for item in report.domain_summaries} == set(ReleaseCandidateDomain)
    assert report.gates_total == len(report.gates) > 0
    assert report.gaps_total == len(report.gaps)
    assert report.public_repo_safe_for_rc_review
    assert report.private_review_required
    validate_release_candidate_report_safe(report)


def test_dependencies_cover_setup_demo_api_hosted_docs_version_and_security():
    dependencies = build_release_candidate_dependencies(settings())
    assert dependencies and all(dependencies.values())
    joined = " ".join(dependencies).casefold()
    for term in ("setup", "demo", "api", "hosted", "docs", "version", "security"):
        assert term in joined


def test_domain_summaries_and_gates_are_complete_and_nonblocking():
    summaries = build_release_candidate_domain_summaries(settings())
    gates = build_release_candidate_gates(settings())
    assert {item.domain for item in summaries} == set(ReleaseCandidateDomain)
    assert all(item.public_safe for item in summaries)
    assert gates and all(item.status is not ReleaseCandidateGateStatus.MISSING for item in gates)
    assert all(item.status is not ReleaseCandidateGateStatus.BLOCKED for item in gates)


def test_gap_command_and_matrix_views_cover_all_domains_safely():
    gaps = build_release_candidate_gap_register(settings())
    commands = build_release_candidate_command_plan(settings())
    matrix = build_release_candidate_matrix(settings())
    assert gaps
    assert any(item.private_review_required for item in gaps)
    assert commands and all(item.safe_read_only for item in commands)
    assert all(not item.live_operation and not item.external_operation for item in commands)
    assert {item.domain for item in matrix} == set(ReleaseCandidateDomain)


def test_no_live_build_publish_release_or_external_flags_are_set():
    report = build_release_candidate_report(settings())
    false_flags = (
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
        "private_report_contents_exposed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
    )
    assert not any(getattr(report, field) for field in false_flags)


@pytest.mark.parametrize(
    "key",
    (
        "release_candidate_require_version_prep",
        "release_candidate_require_setup_experience",
        "release_candidate_require_demo_data",
        "release_candidate_require_api_docs",
        "release_candidate_require_hosted_ui_review",
        "release_candidate_require_docs_site_polish",
        "release_candidate_require_security_closeout",
        "release_candidate_require_final_readiness",
        "release_candidate_require_release_boundary",
        "release_candidate_require_no_build",
        "release_candidate_require_no_publish",
        "release_candidate_require_no_tag",
        "release_candidate_require_no_deploy",
        "release_candidate_require_no_workflow_changes",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(ReleaseCandidateReviewBlockedError):
        build_release_candidate_report(settings(**{key: False}))


def test_validator_rejects_unsafe_flags():
    report = build_release_candidate_report(settings())
    for field in (
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
        "secrets_exposed",
        "production_approval_granted",
        "release_approval_granted",
    ):
        with pytest.raises(ReleaseCandidateReviewBlockedError):
            validate_release_candidate_report_safe(report.model_copy(update={field: True}))


def test_artifacts_are_safe_and_path_traversal_is_blocked():
    report = build_release_candidate_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-release-candidate-", dir="/tmp") as root:
        result = write_release_candidate_artifacts(report, Path(root))
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
        with pytest.raises(ReleaseCandidateReviewBlockedError):
            write_release_candidate_artifacts(report, path)


def test_matrix_csv_neutralizes_formula_injection():
    report = build_release_candidate_report(settings())
    report.matrix[0].evidence = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_release_candidate_matrix_csv(report)


def test_cli_and_make_targets_run_without_persistent_output():
    commands = (
        (".venv/bin/python", "scripts/run_release_candidate_review.py"),
        (".venv/bin/python", "scripts/print_release_candidate_checklist.py"),
        (".venv/bin/python", "scripts/print_release_candidate_gap_register.py"),
        (".venv/bin/python", "scripts/print_release_candidate_command_plan.py"),
        (".venv/bin/python", "scripts/generate_release_candidate_artifacts.py", "--temporary"),
        ("make", "release-candidate-review"),
        ("make", "release-candidate-checklist"),
        ("make", "release-candidate-gap-register"),
        ("make", "release-candidate-command-plan"),
        ("make", "release-candidate-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr


def test_makefile_quality_has_checks_and_no_live_release_targets():
    makefile = (ROOT / "Makefile").read_text()
    quality = " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "release-candidate-review",
        "release-candidate-checklist",
        "release-candidate-gap-register",
        "release-candidate-command-plan",
    ):
        assert target in quality
    assert "release-candidate-artifact-check" not in quality
    headers = {
        line.split(":", 1)[0]
        for line in makefile.splitlines()
        if line and not line.startswith((" ", "\t")) and ":" in line
    }
    assert not headers & {"build", "publish", "release", "tag", "deploy", "docker-build"}


def test_docs_examples_and_navigation_contract():
    docs = {
        ROOT / "docs/release-candidate-review.md",
        ROOT / "docs/release-candidate-checklist.md",
        ROOT / "docs/release-candidate-gap-register.md",
        ROOT / "docs/release-candidate-command-plan.md",
    }
    assert all(path.is_file() for path in docs)
    canonical = "\n".join(path.read_text().casefold() for path in docs)
    for phrase in ("no package build", "no docker build", "no publish", "no tag", "no release"):
        assert phrase in canonical
    assert "no deploy" in canonical and "approval" in canonical
    examples = list((ROOT / "examples/release-candidate-review").iterdir())
    assert "PLACEHOLDER" in "\n".join(path.read_text() for path in examples if path.is_file())
    assert not audit_paths(examples)
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]


def test_public_safety_blocks_outputs_tokens_signing_and_release_claims(tmp_path):
    guide = tmp_path / "release-candidate-review.md"
    assert audit_text(guide, "package_registry_token=private-value")
    assert audit_text(guide, "release_signing_key=private-value")
    assert audit_text(guide, "The package was published and release candidate is approved.")
    assert not audit_text(guide, "No package was built; release is not approved.")
    generated = tmp_path / "release-candidate-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    assert audit_paths([generated])


def test_routes_and_workflows_remain_unchanged():
    assert len(application_routes()) == 81
    assert audit_routes() == []
    workflow_dir = ROOT / ".github/workflows"
    assert not workflow_dir.is_dir() or not any(
        "publish" in path.read_text().casefold() or "release" in path.read_text().casefold()
        for path in workflow_dir.iterdir()
    )

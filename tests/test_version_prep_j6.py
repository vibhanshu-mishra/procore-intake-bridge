from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest
from app.services.version_prep import (
    ARTIFACT_FILES,
    VersionPrepBlockedError,
    build_release_boundary_checklist,
    build_version_prep_report,
    build_version_readiness_matrix,
    collect_package_metadata,
    collect_version_sources,
    render_version_readiness_matrix_csv,
    validate_version_prep_report_safe,
    write_version_prep_artifacts,
)

from app.config import Settings
from app.schemas.version_prep import (
    PackageMetadataStatus,
    ReleaseBoundaryStatus,
    VersionSourceType,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_for_prepared_target_version():
    report = build_version_prep_report(settings())
    assert report.target_version == "0.1.0"
    assert report.version_source_present
    assert report.package_metadata_present
    assert report.changelog_entry_present
    assert report.release_boundary_documented
    assert report.version_sources_total == len(report.version_sources) > 0
    assert report.package_metadata_items_total == len(report.package_metadata) > 0
    assert report.release_boundary_items_total == len(report.release_boundary_checklist) > 0
    validate_version_prep_report_safe(report)


def test_version_sources_are_known_present_and_consistent():
    sources = collect_version_sources(settings())
    assert any(item.source_type is VersionSourceType.APP_VERSION_FILE for item in sources)
    assert all(item.source_type is not VersionSourceType.UNKNOWN for item in sources)
    assert all(item.present and item.consistent_with_target for item in sources)


def test_package_metadata_is_present_or_explicitly_reviewed():
    metadata = collect_package_metadata(settings())
    assert metadata
    assert all(
        item.status is not PackageMetadataStatus.MISSING for item in metadata if item.required
    )
    assert {item.status for item in metadata} <= {
        PackageMetadataStatus.PRESENT,
        PackageMetadataStatus.PLACEHOLDER,
        PackageMetadataStatus.NEEDS_REVIEW,
        PackageMetadataStatus.NOT_APPLICABLE,
    }


def test_release_boundaries_and_readiness_matrix_are_complete():
    boundaries = build_release_boundary_checklist(settings())
    matrix = build_version_readiness_matrix(settings())
    assert boundaries and matrix
    assert all(not item.operation_attempted for item in boundaries)
    assert all(item.status is ReleaseBoundaryStatus.DOCUMENTED for item in boundaries)
    for term in ("build", "publish", "tag", "release", "deploy", "workflow"):
        assert any(
            term in item.code.casefold() or term in item.description.casefold()
            for item in boundaries
        )


def test_no_build_publish_release_or_external_flags_are_set():
    report = build_version_prep_report(settings())
    false_flags = (
        "package_build_attempted",
        "docker_build_attempted",
        "publish_attempted",
        "tag_attempted",
        "release_attempted",
        "deploy_attempted",
        "workflow_changed",
        "github_api_attempted",
        "package_registry_call_attempted",
        "external_call_attempted",
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
        "version_prep_require_version_source",
        "version_prep_require_package_metadata",
        "version_prep_require_changelog_entry",
        "version_prep_require_release_boundary",
        "version_prep_require_no_build",
        "version_prep_require_no_publish",
        "version_prep_require_no_tag",
        "version_prep_require_no_deploy",
        "version_prep_require_no_workflow_changes",
    ),
)
def test_required_settings_fail_closed(key):
    with pytest.raises(VersionPrepBlockedError):
        build_version_prep_report(settings(**{key: False}))


def test_validator_rejects_unsafe_flags():
    report = build_version_prep_report(settings())
    for field in (
        "package_build_attempted",
        "docker_build_attempted",
        "publish_attempted",
        "tag_attempted",
        "release_attempted",
        "deploy_attempted",
        "workflow_changed",
        "github_api_attempted",
        "package_registry_call_attempted",
        "external_call_attempted",
        "secrets_exposed",
        "production_approval_claimed",
        "release_approval_claimed",
    ):
        with pytest.raises(VersionPrepBlockedError):
            validate_version_prep_report_safe(report.model_copy(update={field: True}))


def test_artifact_generation_is_safe_and_traversal_is_blocked():
    report = build_version_prep_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-version-prep-", dir="/tmp") as root:
        result = write_version_prep_artifacts(report, Path(root))
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
        with pytest.raises(VersionPrepBlockedError):
            write_version_prep_artifacts(report, path)


def test_readiness_matrix_csv_neutralizes_formula_injection():
    report = build_version_prep_report(settings())
    report.readiness_matrix[0].area = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_version_readiness_matrix_csv(report)


def test_cli_and_make_targets_run_without_persistent_output():
    commands = (
        (".venv/bin/python", "scripts/run_version_prep_review.py"),
        (".venv/bin/python", "scripts/print_package_metadata_summary.py"),
        (".venv/bin/python", "scripts/print_version_source_map.py"),
        (".venv/bin/python", "scripts/print_release_boundary_checklist.py"),
        (".venv/bin/python", "scripts/generate_version_prep_artifacts.py", "--temporary"),
        ("make", "version-prep-review"),
        ("make", "package-metadata-summary"),
        ("make", "version-source-map"),
        ("make", "release-boundary-checklist"),
        ("make", "version-prep-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr


def test_makefile_has_checks_but_no_new_live_release_targets():
    makefile = (ROOT / "Makefile").read_text()
    quality = " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "version-prep-review",
        "package-metadata-summary",
        "version-source-map",
        "release-boundary-checklist",
    ):
        assert target in quality
    assert "version-prep-artifact-check" not in quality
    target_headers = {
        line.split(":", 1)[0]
        for line in makefile.splitlines()
        if line and not line.startswith(("\t", " ")) and ":" in line
    }
    assert not target_headers & {"build", "publish", "release", "tag", "deploy", "docker-build"}


def test_docs_examples_and_navigation_contract():
    docs = {
        ROOT / "docs/package-metadata-summary.md",
        ROOT / "docs/version-source-map.md",
        ROOT / "docs/release-boundary-checklist.md",
        ROOT / "docs/version-prep-review.md",
    }
    assert all(path.is_file() for path in docs)
    canonical = "\n".join(path.read_text().casefold() for path in docs)
    for phrase in ("no package build", "no publish", "no tag", "no release", "no deploy"):
        assert phrase in canonical
    assert "production approval" in canonical
    examples = list((ROOT / "examples/version-prep").iterdir())
    assert "PLACEHOLDER" in "\n".join(path.read_text() for path in examples if path.is_file())
    assert not audit_paths(examples)
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]


def test_public_safety_blocks_outputs_tokens_signing_keys_and_release_claims(tmp_path):
    guide = tmp_path / "version-prep-review.md"
    assert audit_text(guide, "package_registry_token=private-value")
    assert audit_text(guide, "release_signing_key=private-value")
    assert audit_text(guide, "The package was published and release is approved.")
    assert not audit_text(guide, "No package was built; release is not approved.")
    generated = tmp_path / "version-prep-output" / "report.md"
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

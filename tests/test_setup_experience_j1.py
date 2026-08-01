from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.setup_experience import SetupExperienceStep
from app.services.setup_experience import (
    ARTIFACT_FILES,
    SetupExperienceBlockedError,
    build_setup_command_map,
    build_setup_experience_report,
    build_setup_mode_paths,
    build_setup_prerequisites,
    build_setup_troubleshooting_items,
    render_setup_command_map_csv,
    validate_setup_experience_report_safe,
    write_setup_experience_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_with_all_setup_steps_and_safe_flags():
    report = build_setup_experience_report(settings())
    represented = {
        item.step
        for collection in (
            report.prerequisites,
            report.commands,
            report.command_map,
        )
        for item in collection
    }
    assert represented == set(SetupExperienceStep)
    assert report.setup_is_local_only
    assert report.demo_safe_defaults_required
    assert not report.secrets_required_for_demo

    false_flags = (
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "db_external_connection_attempted",
        "package_build_attempted",
        "publish_attempted",
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
    )
    assert not any(getattr(report, name) for name in false_flags)
    validate_setup_experience_report_safe(report)


def test_prerequisites_and_troubleshooting_cover_local_tools_and_path():
    prerequisites = " ".join(
        f"{item.name} {item.guidance} {item.check_command}"
        for item in build_setup_prerequisites(settings())
    ).casefold()
    troubleshooting = " ".join(
        f"{item.symptom} {item.guidance} {item.check_command or ''}"
        for item in build_setup_troubleshooting_items(settings())
    ).casefold()
    for term in ("git", "python", "pip", "make"):
        assert term in prerequisites
        assert term in troubleshooting
    assert "path" in troubleshooting


def test_command_map_contains_safe_first_run_commands():
    command_map = " ".join(item.command for item in build_setup_command_map(settings()))
    for command in (
        "make first-run",
        "make try-demo",
        "make quality",
        "make safety-check",
        "make docs-site-check",
    ):
        assert command in command_map


def test_demo_and_gated_mode_paths_remain_separate():
    paths = {item.mode.casefold(): item for item in build_setup_mode_paths(settings())}
    assert {"demo", "sandbox", "pilot", "hosted"} <= set(paths)
    assert not paths["demo"].requires_secrets
    assert not paths["demo"].gated
    for mode in ("sandbox", "pilot", "hosted"):
        assert paths[mode].gated
        assert "separate" in paths[mode].description.casefold()


@pytest.mark.parametrize(
    "key",
    (
        "setup_experience_require_demo_safe_defaults",
        "setup_experience_require_no_secrets",
        "setup_experience_require_ignored_outputs",
        "setup_experience_require_local_only",
    ),
)
def test_required_safety_settings_fail_closed(key):
    with pytest.raises(SetupExperienceBlockedError):
        build_setup_experience_report(settings(**{key: False}))


@pytest.mark.parametrize(
    "value",
    (
        {"message": "Demo Mode requires a real admin token"},
        {"message": "production-ready"},
        {"message": "approved for release"},
        {"message": "pilot approved"},
        {"message": "SOC 2 certified"},
        {"github_token": "private-value"},
        {"registry_token": "private-value"},
        {"database_" + "url": "private-value"},
        {"signed_url": "https://unsafe.invalid/file?signature=private-value"},
        {"storage_key": "private/object/key"},
        {"cloud_resource_id": "arn:aws:iam::123456789012:role/private"},
        {"private_report_contents": "private-value"},
    ),
)
def test_validator_blocks_private_material_and_unsafe_claims(value):
    with pytest.raises(SetupExperienceBlockedError):
        validate_setup_experience_report_safe(value)


def test_artifacts_are_sanitized_and_traversal_is_blocked():
    report = build_setup_experience_report(settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-setup-experience-", dir="/tmp") as root:
        result = write_setup_experience_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        assert not result.external_operations
        for relative in result.files:
            validate_setup_experience_report_safe((Path(root) / relative).read_text())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(SetupExperienceBlockedError):
            write_setup_experience_artifacts(report, path)


def test_csv_formula_injection_is_neutralized():
    report = build_setup_experience_report(settings())
    report.command_map[0].purpose = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA_PLACEHOLDER" in render_setup_command_map_csv(report)


def test_cli_and_make_targets_run_without_writing_persistent_output():
    commands = (
        (".venv/bin/python", "scripts/run_setup_experience_review.py"),
        (".venv/bin/python", "scripts/print_first_run_checklist.py"),
        (".venv/bin/python", "scripts/print_local_installer_guide.py"),
        (".venv/bin/python", "scripts/print_setup_troubleshooting_guide.py"),
        (".venv/bin/python", "scripts/generate_setup_experience_artifacts.py", "--temporary"),
        ("make", "setup-experience-review"),
        ("make", "first-run-checklist"),
        ("make", "local-installer-guide"),
        ("make", "setup-troubleshooting-guide"),
        ("make", "setup-experience-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
        validate_setup_experience_report_safe(result.stdout)


def test_docs_examples_navigation_and_quality_contract():
    docs = {
        ROOT / "docs/local-installer-guide.md",
        ROOT / "docs/first-run-checklist.md",
        ROOT / "docs/setup-troubleshooting-guide.md",
        ROOT / "docs/setup-experience-review.md",
    }
    assert all(path.is_file() for path in docs)
    canonical = "\n".join(path.read_text().casefold() for path in docs)
    for phrase in ("local", "demo mode", "no deploy", "no release"):
        assert phrase in canonical
    assert "no secrets" in canonical or "requires no" in canonical
    assert "no production approval" in canonical or "not production approval" in canonical

    examples = "\n".join(
        path.read_text()
        for path in (ROOT / "examples/setup-experience").iterdir()
        if path.is_file()
    )
    assert "PLACEHOLDER" in examples
    assert not audit_paths(list((ROOT / "examples/setup-experience").iterdir()))
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]

    makefile = (ROOT / "Makefile").read_text()
    quality = " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "setup-experience-review",
        "first-run-checklist",
        "local-installer-guide",
        "setup-troubleshooting-guide",
    ):
        assert target in quality
    assert "setup-experience-artifact-check" not in quality


def test_public_safety_allows_negations_and_blocks_unsafe_setup_guidance(tmp_path):
    guide = tmp_path / "setup-experience-review.md"
    assert audit_text(guide, "Demo Mode requires a real admin token.")
    assert audit_text(guide, "This installer is production-ready.")
    assert audit_text(guide, "Pilot is approved.")
    assert not audit_text(guide, "Demo Mode requires no secrets.")
    assert not audit_text(guide, "This does not imply production approval.")
    assert not audit_text(guide, "Pilot is not approved.")

    generated = tmp_path / "setup-experience-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    assert audit_paths([generated])


def test_route_and_workflow_boundaries_are_unchanged():
    assert len(application_routes()) == 81
    assert audit_routes() == []
    workflow_dir = ROOT / ".github/workflows"
    assert not workflow_dir.is_dir() or not any(
        "setup" in path.name.casefold() for path in workflow_dir.iterdir()
    )

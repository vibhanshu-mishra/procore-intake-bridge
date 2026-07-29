import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.private_workspace import (
    PrivateWorkspaceManifest,
    PrivateWorkspaceMode,
    PrivateWorkspaceSection,
)
from app.services.private_workspace import (
    PrivateWorkspaceBlockedError,
    build_private_workspace_manifest,
    build_private_workspace_validation_report,
    validate_existing_private_workspace,
    validate_private_workspace_path,
    write_private_workspace,
)
from app.services.usage_modes import (
    build_demo_mode_readiness,
    build_pilot_mode_readiness,
    build_sandbox_mode_readiness,
    build_usage_mode_doctor_report,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/private-workspace/example_workspace_manifest.json"


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def load_example() -> PrivateWorkspaceManifest:
    return PrivateWorkspaceManifest.model_validate_json(EXAMPLE.read_text())


def with_note(note: str) -> PrivateWorkspaceManifest:
    payload = load_example().model_dump(mode="json")
    payload["notes"] = [note]
    return PrivateWorkspaceManifest.model_validate(payload)


def blocking_codes(manifest: PrivateWorkspaceManifest) -> set[str]:
    report = build_private_workspace_validation_report(manifest, configured())
    return {
        finding.code for finding in report.findings if finding.severity == "blocking"
    }


def test_example_validates_and_modes_are_recognized() -> None:
    assert build_private_workspace_validation_report(
        load_example(), configured()
    ).valid
    for mode in PrivateWorkspaceMode:
        manifest = build_private_workspace_manifest(mode, configured())
        assert manifest.mode == mode
        assert manifest.files


def test_invalid_mode_and_disabled_bootstrap_are_blocked() -> None:
    with pytest.raises(PrivateWorkspaceBlockedError):
        build_private_workspace_manifest("invalid", configured())
    with pytest.raises(PrivateWorkspaceBlockedError):
        build_private_workspace_manifest(
            PrivateWorkspaceMode.PILOT,
            configured(private_workspace_enabled=False),
        )


def test_combined_manifest_has_expected_sections() -> None:
    manifest = build_private_workspace_manifest(
        PrivateWorkspaceMode.SANDBOX_AND_PILOT, configured()
    )
    sections = {item.section for item in manifest.files}
    assert {
        PrivateWorkspaceSection.SANDBOX,
        PrivateWorkspaceSection.DMSA,
        PrivateWorkspaceSection.PERMISSIONS,
        PrivateWorkspaceSection.EVIDENCE,
        PrivateWorkspaceSection.EVIDENCE_REVIEW,
        PrivateWorkspaceSection.PILOT_READINESS,
        PrivateWorkspaceSection.PILOT_APPROVAL,
        PrivateWorkspaceSection.LAUNCH,
        PrivateWorkspaceSection.ROLLBACK,
        PrivateWorkspaceSection.INCIDENT_RESPONSE,
    } <= sections


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("Procore company 87654321", "real_id"),
        ("customer-build.com", "domain"),
        ("Jane Smith", "identity"),
        ("pilot.owner@customer-build.com", "email"),
        ("312-555-0199", "phone"),
        ("client_secret=private-value", "secret"),
        ("Authorization: Bearer fake-private-value", "secret"),
        ("https://files.invalid/x?signature=private-value", "signed_url"),
        ("/Users/operator/private/file.json", "absolute_path"),
        ("PRIVATE_VALUE=private-value", "env_assignment"),
        ("postgresql://operator:placeholder@database.invalid/pilot", "database_url"),
        ("s3://customer-private-bucket/evidence", "storage_url"),
        ('raw payload: {"project": "private"}', "raw_content"),
        ("raw support bundle contents", "raw_content"),
        ("raw smoke report contents", "raw_content"),
        ("raw webhook report contents", "raw_content"),
        ("raw evidence contents", "raw_content"),
        ("PRIVATE_REF_PLACEHOLDER/report.pdf", "binary_reference"),
    ],
)
def test_unsafe_manifest_patterns_are_blocked(value: str, code: str) -> None:
    assert code in blocking_codes(with_note(value))


def test_too_many_files_and_unsafe_paths_are_blocked() -> None:
    payload = load_example().model_dump(mode="json")
    payload["files"] *= 21
    assert "max_files" in blocking_codes(PrivateWorkspaceManifest.model_validate(payload))
    payload = load_example().model_dump(mode="json")
    payload["files"][0]["relative_path"] = "../escape.private.md"
    assert "unsafe_path" in blocking_codes(
        PrivateWorkspaceManifest.model_validate(payload)
    )


def test_generation_is_contained_placeholder_only_and_overwrite_guarded(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private-workspace"
    result = write_private_workspace("sandbox_and_pilot", root)
    assert result.output_directory == "private-workspace"
    assert "workspace-manifest.json" in result.files
    assert all(
        not Path(item).is_absolute() and ".." not in Path(item).parts
        for item in result.files
    )
    contents = "\n".join(
        path.read_text() for path in root.rglob("*") if path.is_file()
    )
    for forbidden in ("Authorization:", "Bearer ", "/Users/", "postgresql://", "@customer"):
        assert forbidden not in contents
    with pytest.raises(PrivateWorkspaceBlockedError):
        write_private_workspace("sandbox_and_pilot", root)
    overwritten = write_private_workspace("sandbox_and_pilot", root, overwrite=True)
    assert overwritten.overwritten is True
    assert validate_existing_private_workspace(root, configured()).valid


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_generation_rejects_unsafe_roots(root: Path) -> None:
    with pytest.raises(PrivateWorkspaceBlockedError):
        write_private_workspace("sandbox", root)


def test_path_validation_blocks_files_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "private-workspace"
    with pytest.raises(PrivateWorkspaceBlockedError):
        validate_private_workspace_path(root.parent / "outside.private.md", root)


def test_existing_workspace_blocks_binary_and_unsafe_text(tmp_path: Path) -> None:
    root = tmp_path / "private-workspace"
    write_private_workspace("sandbox", root)
    (root / "unsafe.pdf").write_bytes(b"%PDF")
    (root / "notes.private.md").write_text("Authorization: Bearer must-not-appear")
    report = validate_existing_private_workspace(root, configured())
    codes = {item.code for item in report.findings}
    assert {"binary_reference", "secret"} <= codes
    assert report.valid is False


def test_cli_workflow_is_safe(tmp_path: Path) -> None:
    commands = [
        [sys.executable, "scripts/print_private_workspace_template.py"],
        [
            sys.executable,
            "scripts/validate_private_workspace.py",
            str(EXAMPLE),
            "--strict",
        ],
        [sys.executable, "scripts/check_private_workspace_git_safety.py"],
    ]
    for command in commands:
        result = subprocess.run(
            command, cwd=ROOT, check=False, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        assert str(ROOT) not in result.stdout
    output = tmp_path / "private-workspace"
    initialized = subprocess.run(
        [
            sys.executable,
            "scripts/init_private_workspace.py",
            "--output-root",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ},
    )
    assert initialized.returncode == 0
    assert str(tmp_path) not in initialized.stdout
    blocked = subprocess.run(
        [
            sys.executable,
            "scripts/init_private_workspace.py",
            "--output-root",
            "../private-workspace",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2


def test_usage_modes_integrate_workspace_without_affecting_demo() -> None:
    demo = build_demo_mode_readiness(configured())
    sandbox = build_sandbox_mode_readiness(configured())
    pilot = build_pilot_mode_readiness(configured())
    assert all(item.requirement != "private_workspace" for item in demo.requirements)
    assert "private_workspace_tools" in {
        item.requirement for item in sandbox.requirements
    }
    assert "private_workspace_tools" in {
        item.requirement for item in pilot.requirements
    }
    sandbox_doctor = build_usage_mode_doctor_report(
        configured(usage_mode="sandbox")
    )
    pilot_doctor = build_usage_mode_doctor_report(configured(usage_mode="pilot"))
    assert any("init-private-workspace" in item for item in sandbox_doctor.recommended_next_steps)
    assert any("init-private-workspace" in item for item in pilot_doctor.recommended_next_steps)


def test_docs_makefile_and_gitignore_describe_c5_boundary() -> None:
    assert "private-workspace/" in (ROOT / ".gitignore").read_text()
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "private-workspace-template",
        "init-private-workspace",
        "validate-private-workspace",
        "private-workspace-git-safety",
        "private-workspace-check",
    ):
        assert f"{target}:" in makefile
    docs = (ROOT / "docs/private-workspace-bootstrap.md").read_text().casefold()
    assert "public repository remains public" in docs
    assert "ignored" in docs
    assert "real customer data never belongs" in docs
    assert json.loads(EXAMPLE.read_text())["mode"] == "sandbox_and_pilot"

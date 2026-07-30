import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.schemas.release_readiness import ReleaseReadinessStatus
from app.services.release_readiness import (
    ARTIFACT_NAMES,
    REQUIRED_CATEGORIES,
    ReleaseReadinessError,
    build_release_readiness_checklist,
    build_release_readiness_report,
    render_release_notes_draft,
    validate_release_readiness_report_safe,
    write_release_readiness_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]


def test_release_checklist_includes_every_required_category() -> None:
    checklist = build_release_readiness_checklist()
    assert set(REQUIRED_CATEGORIES) == {
        item.category for item in checklist.requirements
    }


def test_report_is_advisory_and_public_safe() -> None:
    report = build_release_readiness_report()
    assert report.status in {
        ReleaseReadinessStatus.READY_FOR_MAINTAINER_REVIEW,
        ReleaseReadinessStatus.NEEDS_REVIEW,
    }
    assert report.status != ReleaseReadinessStatus.BLOCKED
    assert report.manual_maintainer_approval_required
    assert not report.release_approved
    assert not report.release_created
    assert not report.tag_created
    assert not report.package_created
    assert not report.deployment_executed
    assert report.known_limitations
    payload = report.model_dump_json()
    assert str(ROOT) not in payload
    assert "must-not-appear" not in payload
    validate_release_readiness_report_safe(report)


def test_release_notes_are_draft_only() -> None:
    notes = render_release_notes_draft(build_release_readiness_report()).casefold()
    assert "draft_placeholder" in notes
    assert "maintainer review required" in notes
    assert "does not create or approve a release" in notes
    assert "known limitations" in notes
    assert "release approved" not in notes


def test_release_artifacts_use_exact_safe_names(tmp_path: Path) -> None:
    root = tmp_path / "release-readiness"
    result = write_release_readiness_artifacts(
        build_release_readiness_report(),
        root,
    )
    assert result.files == ARTIFACT_NAMES
    assert result.output_directory == "release-readiness"
    assert set(item.name for item in root.iterdir()) == set(ARTIFACT_NAMES)
    assert not result.release_created
    assert not result.tag_created
    assert not result.package_created
    assert not result.deployment_executed
    for path in root.iterdir():
        content = path.read_text()
        assert str(tmp_path) not in content
        assert "must-not-appear" not in content


def test_release_artifact_traversal_is_blocked() -> None:
    report = build_release_readiness_report()
    with pytest.raises(ReleaseReadinessError):
        write_release_readiness_artifacts(report, Path("../release-output"))
    with pytest.raises(ReleaseReadinessError):
        write_release_readiness_artifacts(report, Path("."))


@pytest.mark.parametrize(
    "script",
    (
        "check_release_readiness.py",
        "print_release_checklist.py",
        "print_release_notes_draft.py",
    ),
)
def test_nonwriting_release_clis_are_safe(script: str) -> None:
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert str(ROOT) not in result.stdout
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout
    assert "release approved" not in result.stdout.casefold()


def test_generation_cli_writes_only_temp_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "release-readiness"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_release_readiness_artifacts.py",
            "--output-root",
            str(root),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload["files"]) == set(ARTIFACT_NAMES)
    assert payload["output_directory"] == "release-readiness"
    assert str(root) not in result.stdout
    assert set(item.name for item in root.iterdir()) == set(ARTIFACT_NAMES)


def test_release_make_targets_work_without_publish_commands() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "release-checklist",
        "release-readiness",
        "release-notes-draft",
        "release-readiness-artifact-check",
    ):
        assert f"{target}:" in makefile
        result = subprocess.run(
            ["make", target],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    assert "release-readiness-artifact-check" not in quality
    assert "generate_release_readiness_artifacts.py" not in quality
    for forbidden in ("git tag", "gh release", "twine", "docker build", "hatch build"):
        assert forbidden not in makefile.casefold()


def test_release_docs_and_navigation_are_explicitly_manual() -> None:
    for relative in (
        "docs/release-readiness.md",
        "docs/release-checklist.md",
        "docs/release-notes-template.md",
    ):
        assert (ROOT / relative).is_file()
    assert "docs/release-readiness.md" in (ROOT / "README.md").read_text()
    assert "release-readiness.md" in (ROOT / "docs/index.md").read_text()
    reference = (ROOT / "docs/command-reference.md").read_text().casefold()
    assert "make release-readiness" in reference
    readiness = (ROOT / "docs/release-readiness.md").read_text().casefold()
    for phrase in (
        "does not publish",
        "maintainer review",
        "make safety-check",
        "make walkthroughs-check",
        "route audit",
    ):
        assert phrase in readiness


def test_missing_repository_is_blocked(tmp_path: Path) -> None:
    report = build_release_readiness_report(tmp_path)
    assert report.status == ReleaseReadinessStatus.BLOCKED
    assert any(item.blocking for item in report.checklist.requirements)

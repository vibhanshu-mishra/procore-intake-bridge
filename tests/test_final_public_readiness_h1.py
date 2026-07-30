import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.final_public_readiness import FinalPublicReadinessCategory
from app.services.final_public_readiness import (
    ARTIFACT_FILES,
    FinalPublicReadinessBlockedError,
    build_final_public_readiness_report,
    sanitize_final_public_readiness_value,
    validate_final_public_readiness_report_safe,
    write_final_public_readiness_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/final-public-readiness"
FORBIDDEN = (
    "https://",
    "postgresql://",
    "authorization: bearer",
    "-----begin",
    "/users/",
    "/private/",
    "customer.com",
    "approved for release",
    "production-ready",
    "raw_report=",
)


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_report_builds_offline_with_all_categories():
    report = build_final_public_readiness_report(settings())
    assert report.status == "ready_for_maintainer_review"
    assert report.categories_total == len(FinalPublicReadinessCategory)
    assert {item.category for item in report.requirements} == set(
        FinalPublicReadinessCategory
    )
    assert not any(
        (
            report.live_operation_attempted,
            report.external_call_attempted,
            report.deployment_attempted,
            report.release_attempted,
            report.procore_call_attempted,
            report.db_connection_attempted,
            report.cloud_call_attempted,
            report.webhook_registration_attempted,
            report.private_report_contents_exposed,
            report.production_approval_claimed,
        )
    )
    validate_final_public_readiness_report_safe(report)


def test_missing_repository_files_need_review(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = build_final_public_readiness_report(settings())
    assert report.status == "needs_review"
    assert report.categories_needing_review > 0
    assert "required_marker_missing" in report.warnings


def test_unsafe_policy_blocks():
    report = build_final_public_readiness_report(
        settings(final_public_readiness_allow_real_urls=True)
    )
    assert report.status == "blocked"
    assert "unsafe_policy" in report.blockers


def test_sanitizer_masks_private_values():
    value = {
        "url": "https://must-not-appear.invalid",
        "identity": "reviewer=Private Person",
        "secret": "Authorization: Bearer must-not-appear",
        "path": Path("/Users/operator/private"),
    }
    output = json.dumps(sanitize_final_public_readiness_value(value)).casefold()
    assert "must-not-appear" not in output
    assert "private person" not in output
    assert "/users/" not in output


def test_generated_artifacts_are_safe(tmp_path: Path):
    output = tmp_path / "procore-intake-bridge-final-readiness-pytest"
    result = write_final_public_readiness_artifacts(
        build_final_public_readiness_report(settings()), output
    )
    assert result.files == ARTIFACT_FILES
    assert {path.name for path in output.iterdir()} == set(ARTIFACT_FILES)
    contents = "\n".join(
        path.read_text(encoding="utf-8") for path in output.iterdir()
    ).casefold()
    assert not any(value in contents for value in FORBIDDEN)
    assert not result.live_operations
    assert not result.release_attempted
    assert not result.deployment_attempted
    assert not result.private_values_exposed


def test_artifact_traversal_is_blocked():
    with pytest.raises(FinalPublicReadinessBlockedError):
        write_final_public_readiness_artifacts(
            build_final_public_readiness_report(settings()),
            Path("../final-readiness-output"),
        )


@pytest.mark.parametrize(
    "script",
    (
        "run_final_public_readiness_audit.py",
        "print_final_public_readiness_checklist.py",
        "print_public_repo_handoff_summary.py",
    ),
)
def test_nonwriting_h1_clis_are_safe(script):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = (result.stdout + result.stderr).casefold()
    assert not any(value in output for value in FORBIDDEN)


def test_artifact_cli_writes_temp_safely():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_final_public_readiness_artifacts.py"),
            "--temporary",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["files"] == ARTIFACT_FILES
    assert payload["live_operations"] is False


def test_makefile_contract():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = (
        "final-readiness",
        "final-readiness-checklist",
        "public-handoff-summary",
        "final-readiness-artifact-check",
    )
    for target in targets:
        assert f"{target}:" in makefile
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in targets[:3]:
        assert target in quality
    assert targets[3] not in quality


def test_docs_examples_and_navigation_contract():
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    for name in (
        "final-public-readiness.md",
        "public-repository-handoff.md",
        "final-readiness-checklist.md",
    ):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8").casefold()
        assert name in nav
        assert "no live operation" in text
        assert "not release" in text
        assert "production" in text and "pilot approval" in text
    examples = "\n".join(
        path.read_text(encoding="utf-8")
        for path in EXAMPLES.iterdir()
        if path.is_file()
    ).casefold()
    assert "placeholder" in examples
    assert not any(value in examples for value in FORBIDDEN)

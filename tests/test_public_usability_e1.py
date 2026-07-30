import subprocess
import sys
from pathlib import Path

from scripts.audit_public_usability import audit_repository

ROOT = Path(__file__).resolve().parents[1]


def _minimal_repo(root: Path) -> None:
    for name in (
        "README.md",
        "QUICKSTART.md",
        "Makefile",
        ".gitignore",
    ):
        (root / name).write_text("")
    for name in (
        "docs",
        "scripts",
        "examples/sandbox-pilot-flow",
        "examples/private-workspace",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)


def test_public_usability_script_runs_safely() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_public_usability.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Summary:" in result.stdout
    assert "Result: PASS" in result.stdout
    assert str(ROOT) not in result.stdout


def test_audit_fails_when_readme_guidance_is_missing(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    findings = audit_repository(tmp_path, tracked_files=["README.md"])
    assert any(
        item.level == "FAIL" and "README" in item.check for item in findings
    )


def test_audit_detects_missing_required_docs(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    findings = audit_repository(tmp_path, tracked_files=[])
    assert any(
        item.level == "FAIL" and item.check == "required file: docs/troubleshooting.md"
        for item in findings
    )


def test_audit_detects_tracked_generated_output_without_reading_it(
    tmp_path: Path,
) -> None:
    _minimal_repo(tmp_path)
    secret = "must-not-appear-private-value"
    output = tmp_path / "pilot-output" / "report.json"
    output.parent.mkdir()
    output.write_text(secret)
    findings = audit_repository(tmp_path, tracked_files=["pilot-output/report.json"])
    rendered = repr(findings)
    assert any(item.check == "tracked generated/private output" for item in findings)
    assert secret not in rendered
    assert str(tmp_path) not in rendered


def test_audit_detects_unsafe_public_pattern_without_echoing_value(
    tmp_path: Path,
) -> None:
    _minimal_repo(tmp_path)
    secret = "unique-private-credential"
    example = tmp_path / "examples" / "unsafe.md"
    example.write_text(f'client_secret="{secret}"')
    findings = audit_repository(tmp_path, tracked_files=["examples/unsafe.md"])
    assert any(item.check == "unsafe public text pattern" for item in findings)
    assert secret not in repr(findings)


def test_e1_docs_and_friendly_make_targets_exist() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in ("help", "first-run", "public-usability-audit", "safety-check"):
        assert f"{target}:" in makefile
    readme = (ROOT / "README.md").read_text().casefold()
    assert "quickstart.md" in readme
    assert "no procore" in readme
    quickstart = (ROOT / "QUICKSTART.md").read_text().casefold()
    for mode in ("demo mode", "sandbox mode", "pilot mode"):
        assert mode in quickstart
    for name in (
        "docs/command-reference.md",
        "docs/first-run-checklist.md",
        "docs/troubleshooting.md",
        "docs/public-usability-audit.md",
    ):
        assert (ROOT / name).is_file()
        assert Path(name).name in (ROOT / "docs/index.md").read_text()


def test_friendly_commands_do_not_contain_live_actions() -> None:
    makefile = (ROOT / "Makefile").read_text()
    first_run = makefile.split("first-run:", 1)[1].split("\n\n", 1)[0]
    safety = makefile.split("safety-check:", 1)[1].split("\n\n", 1)[0]
    combined = (first_run + safety).casefold()
    for forbidden in (
        "run_sandbox_dmsa_smoke",
        "check_database_connectivity",
        "register",
        "deploy",
    ):
        assert forbidden not in combined

import re
import subprocess
import sys
from pathlib import Path

from scripts.check_walkthroughs import EXPECTED_OUTPUTS, WALKTHROUGHS, check_walkthroughs

ROOT = Path(__file__).resolve().parents[1]


def test_walkthrough_docs_and_examples_exist() -> None:
    for relative in WALKTHROUGHS | EXPECTED_OUTPUTS:
        assert (ROOT / relative).is_file()


def test_walkthrough_index_and_navigation_links() -> None:
    index = (ROOT / "docs/walkthrough-index.md").read_text()
    for name in ("walkthrough-demo.md", "walkthrough-sandbox.md", "walkthrough-pilot.md"):
        assert name in index
    assert "docs/walkthrough-index.md" in (ROOT / "README.md").read_text()
    assert "docs/walkthrough-index.md" in (ROOT / "QUICKSTART.md").read_text()
    assert "walkthrough-index.md" in (ROOT / "docs/index.md").read_text()
    reference = (ROOT / "docs/command-reference.md").read_text()
    for name in ("walkthrough-demo.md", "walkthrough-sandbox.md", "walkthrough-pilot.md"):
        assert name in reference


def test_demo_walkthrough_is_credential_free_and_friendly() -> None:
    text = (ROOT / "docs/walkthrough-demo.md").read_text().casefold()
    for phrase in (
        "no procore credentials",
        "no secrets",
        "no external database",
        "make start",
        "make try-demo",
    ):
        assert phrase in text


def test_sandbox_walkthrough_separates_private_and_live_steps() -> None:
    text = (ROOT / "docs/walkthrough-sandbox.md").read_text().casefold()
    assert "private dmsa" in text
    assert "make prepare-sandbox" in text
    assert "does not\nrun live smoke by default" in text
    assert "do not run it as part of this walkthrough" in text
    assert "never paste credentials" in text


def test_pilot_walkthrough_ends_in_private_review_and_launch_hold() -> None:
    text = (ROOT / "docs/walkthrough-pilot.md").read_text().casefold()
    for phrase in (
        "private workspace",
        "evidence",
        "approval",
        "does not approve a real pilot",
        "launch hold",
        "make prepare-pilot",
    ):
        assert phrase in text


def test_expected_output_is_short_and_placeholder_safe() -> None:
    unsafe = re.compile(
        r"(?i)(?:https?://|(?:postgres(?:ql)?|mysql|sqlite)://|"
        r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|"
        r"(?:/Users/|/home/[^/\s]+/|[A-Z]:\\Users\\)|"
        r"-----BEGIN|(?:company|project)[_-]?id\s*[:=]\s*\d+)"
    )
    for relative in EXPECTED_OUTPUTS:
        text = (ROOT / relative).read_text()
        assert len(text.splitlines()) < 30
        assert not unsafe.search(text)
        if not relative.endswith("README.md"):
            assert "PLACEHOLDER" in text


def test_walkthrough_verifier_passes_and_is_sanitized() -> None:
    findings = check_walkthroughs(ROOT)
    assert not [item for item in findings if item.level == "FAIL"]
    result = subprocess.run(
        [sys.executable, "scripts/check_walkthroughs.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Result: PASS" in result.stdout
    assert str(ROOT) not in result.stdout


def test_walkthrough_verifier_fails_for_missing_docs(tmp_path: Path) -> None:
    findings = check_walkthroughs(tmp_path)
    assert any(item.level == "FAIL" and "required file" in item.check for item in findings)
    assert str(tmp_path) not in repr(findings)


def test_walkthrough_make_targets_are_print_only_and_safe() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "walkthroughs",
        "walkthroughs-check",
        "demo-walkthrough",
        "sandbox-walkthrough",
        "pilot-walkthrough",
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
        assert str(ROOT) not in result.stdout
    sandbox = makefile.split("sandbox-walkthrough:", 1)[1].split("\n\n", 1)[0]
    pilot = makefile.split("pilot-walkthrough:", 1)[1].split("\n\n", 1)[0]
    assert "run_sandbox_dmsa_smoke" not in sandbox
    assert "deploy " not in pilot.casefold()
    assert "no approval" in pilot.casefold()

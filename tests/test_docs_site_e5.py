import shutil
import subprocess
import sys
from pathlib import Path

from scripts.check_docs_site import (
    REQUIRED_GROUPS,
    REQUIRED_NAV_DOCS,
    check_docs_site,
)

ROOT = Path(__file__).resolve().parents[1]


def _copy_docs_site(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", root / "docs")
    for name in ("mkdocs.yml", "README.md", "QUICKSTART.md"):
        shutil.copy2(ROOT / name, root / name)
    return root


def test_mkdocs_config_has_safe_complete_navigation() -> None:
    config = (ROOT / "mkdocs.yml").read_text()
    for group in REQUIRED_GROUPS:
        assert f"- {group}:" in config
    for document in REQUIRED_NAV_DOCS:
        assert f": {document}" in config
        assert (ROOT / "docs" / document).is_file()
    lowered = config.casefold()
    for forbidden in (
        "site_url:",
        "analytics:",
        "google_analytics:",
        "extra_javascript:",
        "gh-deploy",
        "gh-pages",
        "http://",
        "https://",
        str(ROOT).casefold(),
    ):
        assert forbidden not in lowered


def test_docs_site_checker_passes_repository() -> None:
    findings = check_docs_site(ROOT)
    assert findings
    assert not [item for item in findings if item.level == "FAIL"]


def test_docs_site_checker_fails_for_missing_nav_target(tmp_path: Path) -> None:
    root = _copy_docs_site(tmp_path)
    config = root / "mkdocs.yml"
    config.write_text(config.read_text() + "\n  - Missing: missing-page.md\n")
    findings = check_docs_site(root)
    assert any(item.level == "FAIL" and item.check == "nav targets" for item in findings)


def test_docs_site_checker_fails_for_hosting_or_analytics(tmp_path: Path) -> None:
    root = _copy_docs_site(tmp_path)
    config = root / "mkdocs.yml"
    config.write_text(
        config.read_text()
        + "\nsite_url: https://docs.example.invalid\nanalytics:\n  provider: example\n"
    )
    findings = check_docs_site(root)
    assert any(
        item.level == "FAIL" and item.check == "hosting and tracking config"
        for item in findings
    )


def test_docs_site_cli_output_is_sanitized() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_docs_site.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "0 failed" in result.stdout
    assert str(ROOT) not in result.stdout
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout


def test_preview_instructions_are_local_only() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/print_docs_preview_instructions.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout.casefold()
    assert "local only" in output
    assert "mkdocs is optional" in output
    assert "does not install mkdocs automatically" in output
    assert "does not" in output and "publish" in output
    assert "gh-deploy" not in output
    assert "http://" not in output and "https://" not in output


def test_docs_make_targets_are_nonwriting() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in ("docs-site-check", "docs-preview-instructions", "docs-map"):
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
    assert "docs-site-check" in quality
    assert "docs-preview-instructions" in quality
    assert "mkdocs build" not in quality
    assert "mkdocs serve" not in quality
    assert "gh-deploy" not in makefile.casefold()


def test_docs_site_guidance_is_linked_and_explicit() -> None:
    assert "docs/docs-site.md" in (ROOT / "README.md").read_text()
    assert "docs/docs-site.md" in (ROOT / "QUICKSTART.md").read_text()
    assert "docs-site.md" in (ROOT / "docs/index.md").read_text()
    guide = (ROOT / "docs/docs-site.md").read_text().casefold()
    for phrase in (
        "local-only",
        "not published by this repository",
        "no github pages automation",
        "mkdocs is optional",
        "not required for demo mode",
    ):
        assert phrase in guide
    navigation = (ROOT / "docs/docs-navigation.md").read_text().casefold()
    assert "reading order" in navigation
    assert all(mode in navigation for mode in ("demo", "sandbox", "pilot"))


def test_docs_outputs_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text()
    for pattern in (
        "site/",
        "docs-site-output/",
        "mkdocs-site-output/",
        "*.docs-site-report.json",
        "*.docs-site-report.md",
    ):
        assert pattern in ignored

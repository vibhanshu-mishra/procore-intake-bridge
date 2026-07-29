import json
from pathlib import Path

from scripts.audit_public_safety import audit_paths
from scripts.audit_routes_read_only import audit_routes


def test_readme_public_truth_and_quick_start():
    readme = Path("README.md").read_text().casefold()
    for concept in (
        "read-only",
        "no procore write",
        "dmsa",
        "pyprocore",
        "live mode is disabled",
        "not affiliated",
        "python3 -m venv",
    ):
        assert concept in readme


def test_documentation_home_links_key_material():
    index = Path("docs/index.md").read_text().casefold()
    for filename in (
        "architecture.md",
        "dmsa-credential-profiles.md",
        "polling-worker.md",
        "webhooks.md",
        "attachment-storage.md",
        "onboarding-packets.md",
        "admin-dashboard.md",
        "deployment-hardening.md",
        "operations-runbook.md",
        "safety-model.md",
        "roadmap.md",
        "public-launch-checklist.md",
    ):
        assert filename in index


def test_public_project_documents_exist():
    for filename in (
        "docs/project-status.md",
        "docs/public-launch-checklist.md",
        "docs/roadmap.md",
        "examples/README.md",
        "examples/demo-flow.md",
        "CONTRIBUTING.md",
        "SUPPORT.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
    ):
        assert Path(filename).is_file()


def test_demo_is_fixture_safe_and_placeholder_only():
    demo = Path("examples/demo-flow.md").read_text().casefold()
    assert "fixture" in demo
    assert "fake" in demo
    assert "placeholder" in demo
    assert "dry_run=true" in demo
    assert "no credentials" in demo
    assert "live procore" in demo
    assert "http://127.0.0.1" in demo
    assert "signature=" not in demo


def test_public_safety_audit_detects_without_echoing_value(tmp_path, capsys):
    secret = "highly-sensitive-credential"
    unsafe = tmp_path / "unsafe.txt"
    unsafe.write_text(f'client_secret="{secret}"')
    issues = audit_paths([unsafe])
    assert len(issues) == 1
    assert secret not in json.dumps(
        [{"path": str(issue.path), "type": issue.issue_type} for issue in issues]
    )
    assert secret not in capsys.readouterr().out


def test_public_safety_audit_allows_placeholders(tmp_path):
    safe = tmp_path / "safe.env.example"
    safe.write_text("client_secret=replace_me_placeholder")
    assert audit_paths([safe]) == []


def test_route_audit_passes_without_calling_routes():
    assert audit_routes() == []


def test_makefile_quality_is_local_and_docker_optional():
    makefile = Path("Makefile").read_text().casefold()
    for target in (
        "test:",
        "lint:",
        "compile:",
        "pip-check:",
        "safety-audit:",
        "route-audit:",
        "quality:",
    ):
        assert target in makefile
    assert "\tdocker " not in makefile

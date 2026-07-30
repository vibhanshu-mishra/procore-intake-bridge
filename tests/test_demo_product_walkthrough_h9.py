from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.services.demo_product_walkthrough import (
    STEP_GROUPS,
    DemoProductWalkthroughBlockedError,
    build_demo_product_walkthrough_report,
    build_demo_product_walkthrough_steps,
    render_demo_evaluation_checklist,
    render_demo_next_steps_markdown,
    render_demo_product_tour_markdown,
    validate_demo_product_walkthrough_report_safe,
    write_demo_product_walkthrough_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def test_report_builds_offline_with_all_expected_groups():
    report = build_demo_product_walkthrough_report(_settings())
    assert tuple(step.group for step in report.steps) == STEP_GROUPS
    assert report.steps_total == 10
    assert report.steps_ready == 10
    assert report.fake_data_required is True
    assert report.demo_only is True
    assert report.live_operation_attempted is False
    assert report.procore_call_attempted is False
    assert report.external_call_attempted is False
    assert report.db_external_connection_attempted is False
    assert report.cloud_call_attempted is False
    assert report.deployment_attempted is False
    assert report.release_attempted is False
    validate_demo_product_walkthrough_report_safe(report)


def test_unsafe_settings_fail_closed():
    with pytest.raises(DemoProductWalkthroughBlockedError):
        build_demo_product_walkthrough_report(_settings(demo_walkthrough_allow_real_urls=True))


@pytest.mark.parametrize(
    "unsafe",
    [
        {"raw_payload_json": {"fake": True}},
        {"source_url": "hidden"},
        {"storage_key": "hidden"},
        {"message": "https://unsafe.invalid/value"},
        {"message": "/Users/example/private"},
        {"message": "client_secret=unsafe"},
        {"message": "Demo walkthrough is production-ready"},
        {"message": "Demo walkthrough approval granted"},
    ],
)
def test_safety_validator_blocks_private_content_and_claims(unsafe):
    with pytest.raises(DemoProductWalkthroughBlockedError):
        validate_demo_product_walkthrough_report_safe(unsafe)


def test_renderers_are_sanitized_and_describe_boundaries():
    report = build_demo_product_walkthrough_report(_settings())
    rendered = "\n".join(
        (
            render_demo_product_tour_markdown(report),
            render_demo_evaluation_checklist(report),
            render_demo_next_steps_markdown(report),
        )
    )
    assert "Fake data only" in rendered
    assert "make product-dashboard-check" in rendered
    assert "private, manually gated" in rendered
    assert "No Procore" in rendered
    validate_demo_product_walkthrough_report_safe(rendered)


def test_missing_repository_components_need_review(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    steps = build_demo_product_walkthrough_steps(_settings())
    assert any(step.status.value == "needs_review" for step in steps)
    assert any(step.findings for step in steps)


def test_artifact_path_traversal_and_unapproved_absolute_roots_are_blocked():
    report = build_demo_product_walkthrough_report(_settings())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-demo-output")):
        with pytest.raises(DemoProductWalkthroughBlockedError):
            write_demo_product_walkthrough_artifacts(report, path)


def test_temp_artifacts_are_safe_and_complete():
    report = build_demo_product_walkthrough_report(_settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-demo-product-", dir="/tmp") as directory:
        result = write_demo_product_walkthrough_artifacts(report, Path(directory))
        assert set(result.files) == {
            "demo.demo-product-tour.md",
            "demo.demo-evaluation-checklist.md",
            "demo.demo-walkthrough-report.json",
            "demo.demo-walkthrough-report.md",
        }
        for name in result.files:
            content = (Path(directory) / name).read_text(encoding="utf-8")
            validate_demo_product_walkthrough_report_safe(content)


def test_cli_and_make_targets_run():
    commands = (
        [".venv/bin/python", "scripts/print_demo_product_tour.py"],
        [".venv/bin/python", "scripts/check_demo_product_walkthrough.py"],
        [".venv/bin/python", "scripts/print_demo_evaluation_checklist.py"],
        [
            ".venv/bin/python",
            "scripts/generate_demo_product_walkthrough_artifacts.py",
            "--temporary",
        ],
        ["make", "demo-product-tour"],
        ["make", "demo-product-check"],
        ["make", "demo-evaluation-checklist"],
        ["make", "demo-product-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_makefile_and_quality_contracts():
    required = (
        "docs/demo-product-walkthrough.md",
        "docs/demo-evaluation-checklist.md",
        "examples/demo-product-walkthrough/README.md",
        "examples/demo-product-walkthrough/demo_product_tour.example.md",
        "examples/demo-product-walkthrough/demo_evaluation_checklist.example.md",
    )
    for relative in required:
        assert (ROOT / relative).is_file()
    docs = (ROOT / "docs/demo-product-walkthrough.md").read_text().casefold()
    for phrase in ("fake data", "no procore call", "no live", "private report"):
        assert phrase in docs
    makefile = (ROOT / "Makefile").read_text()
    assert "quality: demo-product-check demo-product-tour demo-evaluation-checklist" in makefile
    quality_lines = "\n".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "demo-product-artifact-check" not in quality_lines


def test_h9_adds_no_route_and_route_audit_remains_green():
    from scripts.audit_routes_read_only import application_routes, audit_routes

    assert not any(route.path.startswith("/demo-product") for route in application_routes())
    assert audit_routes() == []

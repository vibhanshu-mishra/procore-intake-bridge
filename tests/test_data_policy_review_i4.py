from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.data_policy_review import (
    DataClassification,
    DataRedactionBoundary,
    DataRetentionBoundary,
)
from app.services.data_policy_review import (
    ARTIFACT_FILES,
    IGNORED_OUTPUTS,
    DataPolicyReviewBlockedError,
    build_data_policy_review_report,
    render_data_handling_checklist_markdown,
    render_data_policy_review_markdown,
    render_data_retention_map_markdown,
    render_generated_output_inventory_csv,
    render_redaction_boundary_map_markdown,
    validate_data_policy_review_report_safe,
    write_data_policy_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_report_builds_offline_with_complete_boundaries():
    report = build_data_policy_review_report(_settings())
    assert report.status == "needs_review"
    assert report.decision == "data_policy_needs_review"
    assert set(report.classifications) == set(DataClassification)
    assert {item.boundary for item in report.retention_boundaries} == set(DataRetentionBoundary)
    assert set(report.redaction_boundaries) == set(DataRedactionBoundary)
    assert report.classifications_total == 13
    assert report.retention_boundaries_total == 15
    assert report.redaction_boundaries_total == 12
    assert report.generated_output_patterns_total == 11
    assert all(item.ignored for item in report.generated_output_inventory)
    assert not any(
        (
            report.destructive_deletion_implemented,
            report.live_scan_attempted,
            report.external_call_attempted,
            report.procore_call_attempted,
            report.cloud_call_attempted,
            report.db_external_connection_attempted,
            report.scanner_attempted,
            report.private_report_contents_exposed,
            report.secrets_exposed,
            report.raw_payloads_exposed,
            report.urls_exposed,
            report.signed_urls_exposed,
            report.private_paths_exposed,
            report.storage_keys_exposed,
            report.original_filenames_exposed,
            report.attachment_contents_exposed,
            report.ids_exposed,
            report.real_domains_exposed,
            report.legal_compliance_claimed,
            report.certification_claimed,
            report.production_approval_claimed,
        )
    )
    validate_data_policy_review_report_safe(report)


@pytest.mark.parametrize(
    "override",
    (
        {"data_policy_review_require_placeholders": False},
        {"data_policy_review_require_raw_payload_redaction": False},
        {"data_policy_review_require_secret_redaction": False},
        {"data_policy_review_require_url_redaction": False},
        {"data_policy_review_require_path_redaction": False},
        {"data_policy_review_require_attachment_content_exclusion": False},
        {"data_policy_review_require_export_safety_flags": False},
        {"data_policy_review_require_generated_output_ignores": False},
        {"data_policy_review_allow_real_identities": True},
        {"data_policy_review_allow_real_domains": True},
        {"data_policy_review_allow_real_urls": True},
        {"data_policy_review_allow_report_contents": True},
        {"data_policy_review_allow_private_paths": True},
    ),
)
def test_unsafe_settings_fail_closed(override):
    with pytest.raises(DataPolicyReviewBlockedError):
        build_data_policy_review_report(_settings(**override))


@pytest.mark.parametrize(
    "unsafe",
    (
        {"raw_payload": "private-value"},
        {"source_url": "private-value"},
        {"signed_url": "private-value"},
        {"database_url": "private-value"},
        {"storage_key": "private-value"},
        {"original_filename": "private-value"},
        {"attachment_content": "private-value"},
        {"private_path": "private-value"},
        {"deletion_log": "private-value"},
        {"message": "reviewer@example.com"},
        {"message": "Authorization: Bearer raw-token-value"},
        {"message": "This system is GDPR compliant"},
        {"message": "This review is production-ready"},
        {"message": "Pilot approved"},
    ),
)
def test_validator_blocks_private_material_and_claims(unsafe):
    with pytest.raises(DataPolicyReviewBlockedError):
        validate_data_policy_review_report_safe(unsafe)


def test_renderers_and_csv_are_safe():
    report = build_data_policy_review_report(_settings())
    report.generated_output_inventory[0].pattern = "=FORMULA_PLACEHOLDER"
    csv_text = render_generated_output_inventory_csv(report)
    assert "'=FORMULA_PLACEHOLDER" in csv_text
    rendered = "\n".join(
        (
            render_data_policy_review_markdown(report),
            render_data_retention_map_markdown(report),
            render_redaction_boundary_map_markdown(report),
            render_data_handling_checklist_markdown(report),
            csv_text,
        )
    )
    validate_data_policy_review_report_safe(rendered)


def test_artifact_roots_fail_closed():
    report = build_data_policy_review_report(_settings())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-data-output")):
        with pytest.raises(DataPolicyReviewBlockedError):
            write_data_policy_review_artifacts(report, path)


def test_temp_artifacts_are_complete_and_safe():
    report = build_data_policy_review_report(_settings())
    with TemporaryDirectory(prefix="procore-intake-bridge-data-policy-", dir="/tmp") as directory:
        result = write_data_policy_review_artifacts(report, Path(directory))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        assert not result.deletion_operations
        for name in result.files:
            validate_data_policy_review_report_safe(
                (Path(directory) / name).read_text(encoding="utf-8")
            )


def test_cli_and_make_targets_run():
    commands = (
        [".venv/bin/python", "scripts/run_data_policy_review.py"],
        [".venv/bin/python", "scripts/print_data_retention_map.py"],
        [".venv/bin/python", "scripts/print_redaction_boundary_map.py"],
        [".venv/bin/python", "scripts/print_data_handling_checklist.py"],
        [".venv/bin/python", "scripts/generate_data_policy_review_artifacts.py", "--temporary"],
        ["make", "data-policy-review"],
        ["make", "data-retention-map"],
        ["make", "redaction-boundary-map"],
        ["make", "data-handling-checklist"],
        ["make", "data-policy-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_ignore_and_quality_contracts():
    required = (
        "docs/data-retention-redaction-policy.md",
        "docs/data-retention-map.md",
        "docs/redaction-boundary-map.md",
        "docs/data-handling-checklist.md",
        "examples/data-policy-review/README.md",
        "examples/data-policy-review/example_data_retention_map.md",
        "examples/data-policy-review/example_redaction_boundary_map.md",
        "examples/data-policy-review/example_data_handling_checklist.md",
        "examples/data-policy-review/example_generated_output_inventory.csv",
    )
    assert all((ROOT / path).is_file() for path in required)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(pattern in gitignore for pattern in IGNORED_OUTPUTS)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert (
        "quality: data-policy-review data-retention-map redaction-boundary-map "
        "data-handling-checklist" in makefile
    )
    assert "quality: data-policy-artifact-check" not in makefile
    docs = (ROOT / required[0]).read_text(encoding="utf-8").casefold()
    for phrase in (
        "offline data policy/redaction review",
        "no live scan",
        "no destructive deletion",
        "no purge jobs",
        "not legal compliance certification",
    ):
        assert phrase in docs


def test_public_safety_catches_claims_material_and_generated_outputs(tmp_path):
    path = tmp_path / "data-policy-review.md"
    assert audit_text(path, "This review is production-ready.")
    assert audit_text(path, "raw_payload=private-value")
    generated = tmp_path / "data-policy-review-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder", encoding="utf-8")
    assert audit_paths([generated])


def test_existing_audits_pass_and_no_route_was_added():
    routes = application_routes()
    assert len(routes) == 81
    assert not any("DELETE" in (route.methods or set()) for route in routes)
    assert audit_routes() == []

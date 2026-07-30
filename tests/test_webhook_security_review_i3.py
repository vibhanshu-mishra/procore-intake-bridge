from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.webhook_security_review import WebhookSecurityCategory
from app.services.webhook_security_review import (
    ARTIFACT_FILES,
    BOUNDARY_NAMES,
    IGNORED_OUTPUTS,
    WebhookSecurityReviewBlockedError,
    build_webhook_fixture_matrix,
    build_webhook_security_review_report,
    render_webhook_fixture_matrix_csv,
    render_webhook_replay_checklist_markdown,
    render_webhook_security_review_markdown,
    render_webhook_signature_boundary_markdown,
    validate_webhook_security_review_report_safe,
    write_webhook_security_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import (
    WEBHOOK_SIGNATURE_POST_PATHS,
    application_routes,
    audit_routes,
)

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_report_builds_offline_with_expected_categories_and_boundaries():
    report = build_webhook_security_review_report(_settings())
    assert report.status == "needs_review"
    assert report.decision == "webhook_security_needs_review"
    assert set(report.categories) == set(WebhookSecurityCategory)
    assert tuple(item.name for item in report.boundaries) == BOUNDARY_NAMES
    assert report.categories_total == 12
    assert report.scenarios_total == 12
    assert report.controls_total >= 7
    assert report.webhook_routes_total == 5
    assert report.webhook_post_routes_total == 3
    assert report.signature_verification_documented
    assert report.constant_time_compare_documented
    assert report.replay_boundary_documented
    assert report.deduplication_documented
    assert report.redacted_failures_documented
    assert {
        "timestamp_replay_window_needs_review",
        "replay_route_access_needs_review",
        "signature_runtime_configuration_needs_review",
    } <= {item.code for item in report.findings}
    assert not any(
        (
            report.live_replay_attempted,
            report.webhook_registration_attempted,
            report.external_call_attempted,
            report.procore_call_attempted,
            report.cloud_call_attempted,
            report.db_external_connection_attempted,
            report.scanner_attempted,
            report.private_report_contents_exposed,
            report.secrets_exposed,
            report.webhook_secrets_exposed,
            report.live_headers_exposed,
            report.live_payloads_exposed,
            report.ids_exposed,
            report.real_urls_exposed,
            report.real_domains_exposed,
            report.private_paths_exposed,
            report.certification_claimed,
            report.production_approval_claimed,
        )
    )
    validate_webhook_security_review_report_safe(report)


def test_fixture_matrix_is_fake_and_safe():
    matrix = build_webhook_fixture_matrix(_settings())
    assert len(matrix) == 11
    assert all(item.placeholder_only for item in matrix)
    assert not any(
        item.live_payload or item.live_headers or item.signature_included for item in matrix
    )


def test_webhook_receiver_routes_remain_signature_bound():
    from app.schemas.auth_boundary_audit import (
        AuthBoundaryMethodRisk,
        AuthBoundaryProtectionType,
    )
    from app.services.auth_boundary_audit import classify_route_auth_boundary

    routes = {
        route.path: route
        for route in application_routes()
        if route.path in WEBHOOK_SIGNATURE_POST_PATHS
    }
    assert set(routes) == WEBHOOK_SIGNATURE_POST_PATHS
    for route in routes.values():
        item = classify_route_auth_boundary(route)
        assert item.protection_type is AuthBoundaryProtectionType.WEBHOOK_SIGNATURE_REQUIRED
        assert item.method_risk is AuthBoundaryMethodRisk.WEBHOOK_POST_SIGNATURE_REQUIRED


@pytest.mark.parametrize(
    "override",
    (
        {"webhook_security_review_require_placeholders": False},
        {"webhook_security_review_require_signature_verification": False},
        {"webhook_security_review_require_constant_time_compare": False},
        {"webhook_security_review_require_replay_boundary": False},
        {"webhook_security_review_require_deduplication": False},
        {"webhook_security_review_require_redacted_failures": False},
        {"webhook_security_review_require_no_header_logging": False},
        {"webhook_security_review_require_no_live_replay": False},
        {"webhook_security_review_allow_real_identities": True},
        {"webhook_security_review_allow_real_domains": True},
        {"webhook_security_review_allow_real_urls": True},
        {"webhook_security_review_allow_report_contents": True},
        {"webhook_security_review_allow_private_paths": True},
    ),
)
def test_unsafe_policy_fails_closed(override):
    with pytest.raises(WebhookSecurityReviewBlockedError):
        build_webhook_security_review_report(_settings(**override))


@pytest.mark.parametrize(
    "unsafe",
    (
        {"source_url": "placeholder"},
        {"message": "https://unsafe.invalid/hook"},
        {"message": "reviewer@example.com"},
        {"message": "/Users/example/private"},
        {"message": "Authorization: Bearer raw-token-value"},
        {"webhook_secret": "raw-secret-value"},
        {"raw_body": "live-value"},
        {"message": "live webhook payload: raw-value"},
        {"message": "The review is production-ready"},
        {"message": "Security certified"},
    ),
)
def test_validator_blocks_private_material_and_claims(unsafe):
    with pytest.raises(WebhookSecurityReviewBlockedError):
        validate_webhook_security_review_report_safe(unsafe)


def test_renderers_are_safe_and_csv_neutralizes_formulas():
    report = build_webhook_security_review_report(_settings())
    report.fixture_matrix[0].fixture_name = "=FORMULA_PLACEHOLDER"
    csv_text = render_webhook_fixture_matrix_csv(report)
    assert "'=FORMULA_PLACEHOLDER" in csv_text
    rendered = "\n".join(
        (
            render_webhook_security_review_markdown(report),
            render_webhook_signature_boundary_markdown(report),
            render_webhook_replay_checklist_markdown(report),
            csv_text,
        )
    )
    assert "No live replay" in rendered
    validate_webhook_security_review_report_safe(rendered)


def test_artifact_roots_fail_closed():
    report = build_webhook_security_review_report(_settings())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-webhook-output")):
        with pytest.raises(WebhookSecurityReviewBlockedError):
            write_webhook_security_review_artifacts(report, path)


def test_temp_artifacts_are_complete_and_safe():
    report = build_webhook_security_review_report(_settings())
    with TemporaryDirectory(
        prefix="procore-intake-bridge-webhook-security-", dir="/tmp"
    ) as directory:
        result = write_webhook_security_review_artifacts(report, Path(directory))
        assert set(result.files) == set(ARTIFACT_FILES)
        for name in result.files:
            validate_webhook_security_review_report_safe(
                (Path(directory) / name).read_text(encoding="utf-8")
            )


def test_cli_and_make_targets_run():
    commands = (
        [".venv/bin/python", "scripts/run_webhook_security_review.py"],
        [".venv/bin/python", "scripts/print_webhook_signature_boundary.py"],
        [".venv/bin/python", "scripts/print_webhook_replay_checklist.py"],
        [
            ".venv/bin/python",
            "scripts/generate_webhook_security_review_artifacts.py",
            "--temporary",
        ],
        ["make", "webhook-security-review"],
        ["make", "webhook-signature-boundary"],
        ["make", "webhook-replay-checklist"],
        ["make", "webhook-security-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_ignore_and_quality_contracts():
    required = (
        "docs/webhook-replay-signature-hardening.md",
        "docs/webhook-signature-boundary.md",
        "docs/webhook-replay-checklist.md",
        "examples/webhook-security-review/README.md",
        "examples/webhook-security-review/example_webhook_signature_boundary.md",
        "examples/webhook-security-review/example_webhook_replay_checklist.md",
        "examples/webhook-security-review/example_webhook_fixture_matrix.csv",
    )
    assert all((ROOT / path).is_file() for path in required)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(pattern in gitignore for pattern in IGNORED_OUTPUTS)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert (
        "quality: webhook-security-review webhook-signature-boundary webhook-replay-checklist"
        in makefile
    )
    quality = "\n".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "webhook-security-artifact-check" not in quality
    docs = (ROOT / required[0]).read_text(encoding="utf-8").casefold()
    for phrase in (
        "offline webhook security review",
        "no live webhook replay",
        "no webhook registration",
        "not production approval",
        "security certification",
    ):
        assert phrase in docs


def test_public_safety_catches_claims_material_and_generated_outputs(tmp_path):
    path = tmp_path / "webhook-security-review.md"
    assert audit_text(path, "This webhook review is production-ready.")
    assert audit_text(path, "live_webhook_payload=raw-value")
    generated = tmp_path / "webhook-security-review-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder", encoding="utf-8")
    assert audit_paths([generated])


def test_existing_audits_pass_and_no_route_was_added():
    assert len(application_routes()) == 81
    assert audit_routes() == []

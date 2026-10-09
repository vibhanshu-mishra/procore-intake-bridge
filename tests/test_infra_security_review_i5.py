from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.infra_security_review import (
    DatabaseBoundary,
    InfraSecurityCategory,
    InfraSecurityFinding,
    SecretBoundary,
    StorageBoundary,
)
from app.services.infra_security_review import (
    ARTIFACT_FILES,
    IGNORED_OUTPUTS,
    InfraSecurityReviewBlockedError,
    build_infra_security_review_policy,
    build_infra_security_review_report,
    render_database_boundary_map_markdown,
    render_infra_provider_matrix_csv,
    render_infra_security_checklist_markdown,
    render_infra_security_review_markdown,
    render_secret_boundary_map_markdown,
    render_storage_boundary_map_markdown,
    validate_infra_security_review_report_safe,
    write_infra_security_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_report_builds_offline_with_complete_boundaries():
    report = build_infra_security_review_report(_settings())
    assert report.status == "needs_review"
    assert report.decision == "infra_security_needs_review"
    assert set(report.categories) == set(InfraSecurityCategory)
    assert set(report.secret_boundaries) == set(SecretBoundary)
    assert set(report.storage_boundaries) == set(StorageBoundary)
    assert set(report.database_boundaries) == set(DatabaseBoundary)
    assert report.categories_total == 18
    assert report.secret_boundaries_total == 12
    assert report.storage_boundaries_total == 10
    assert report.database_boundaries_total == 8
    assert report.provider_matrix_items_total == 15
    assert not any(
        (
            report.secret_values_exposed,
            report.secret_retrieval_attempted,
            report.storage_access_attempted,
            report.presigned_urls_exposed,
            report.storage_keys_exposed,
            report.db_connection_attempted,
            report.migration_attempted,
            report.backup_attempted,
            report.restore_attempted,
            report.dump_inspection_attempted,
            report.external_call_attempted,
            report.procore_call_attempted,
            report.cloud_call_attempted,
            report.scanner_attempted,
            report.private_report_contents_exposed,
            report.secrets_exposed,
            report.urls_exposed,
            report.signed_urls_exposed,
            report.private_paths_exposed,
            report.ids_exposed,
            report.real_domains_exposed,
            report.legal_compliance_claimed,
            report.certification_claimed,
            report.production_approval_claimed,
        )
    )
    validate_infra_security_review_report_safe(report)


@pytest.mark.parametrize(
    "override",
    (
        {"infra_security_review_require_placeholders": False},
        {"infra_security_review_require_secret_references": False},
        {"infra_security_review_require_no_secret_values": False},
        {"infra_security_review_require_secret_masking": False},
        {"infra_security_review_require_storage_metadata_only": False},
        {"infra_security_review_require_no_presigned_urls": False},
        {"infra_security_review_require_no_storage_keys": False},
        {"infra_security_review_require_db_url_references": False},
        {"infra_security_review_require_db_operation_gates": False},
        {"infra_security_review_require_migration_gates": False},
        {"infra_security_review_require_backup_restore_plans": False},
        {"infra_security_review_allow_real_identities": True},
        {"infra_security_review_allow_real_domains": True},
        {"infra_security_review_allow_real_urls": True},
        {"infra_security_review_allow_report_contents": True},
        {"infra_security_review_allow_private_paths": True},
    ),
)
def test_unsafe_settings_fail_closed(override):
    with pytest.raises(InfraSecurityReviewBlockedError):
        build_infra_security_review_report(_settings(**override))


@pytest.mark.parametrize(
    "unsafe",
    (
        {"secret_value": "private-value"},
        {"password": "private-value"},
        {"api_key": "private-value"},
        {"admin_token": "secret-value"},
        {"webhook_secret": "secret-value"},
        {"dmsa_client_secret": "secret-value"},
        {"database_url": "private-value"},
        {"signed_url": "private-value"},
        {"presigned_url": "private-value"},
        {"storage_key": "private-value"},
        {"object_key": "private-value"},
        {"db_dump_content": "private-value"},
        {"backup_archive_content": "private-value"},
        {"migration_log": "private-value"},
        {"message": "reviewer@example.com"},
        {"message": "Authorization: Bearer raw-token-value"},
        {"message": "This system is GDPR compliant"},
        {"message": "This review is production-ready"},
        {"message": "Pilot approved"},
    ),
)
def test_validator_blocks_private_material_and_claims(unsafe):
    with pytest.raises(InfraSecurityReviewBlockedError):
        validate_infra_security_review_report_safe(unsafe)


def test_renderers_and_csv_are_safe():
    report = build_infra_security_review_report(_settings())
    report.provider_matrix[0].provider = "=FORMULA_PLACEHOLDER"
    csv_text = render_infra_provider_matrix_csv(report)
    assert "'=FORMULA_PLACEHOLDER" in csv_text
    rendered = "\n".join(
        (
            render_infra_security_review_markdown(report),
            render_secret_boundary_map_markdown(report),
            render_storage_boundary_map_markdown(report),
            render_database_boundary_map_markdown(report),
            render_infra_security_checklist_markdown(report),
            csv_text,
        )
    )
    validate_infra_security_review_report_safe(rendered)


def test_artifact_roots_fail_closed():
    report = build_infra_security_review_report(_settings())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-infra-output")):
        with pytest.raises(InfraSecurityReviewBlockedError):
            write_infra_security_review_artifacts(report, path)


def test_temp_artifacts_are_complete_and_safe():
    report = build_infra_security_review_report(_settings())
    with TemporaryDirectory(
        prefix="procore-intake-bridge-infra-security-", dir="/tmp"
    ) as directory:
        result = write_infra_security_review_artifacts(report, Path(directory))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not any(
            (
                result.live_operations,
                result.secret_retrieval,
                result.storage_access,
                result.database_operations,
            )
        )
        for name in result.files:
            validate_infra_security_review_report_safe(
                (Path(directory) / name).read_text(encoding="utf-8")
            )


def test_artifact_builder_uses_only_public_policy_values():
    database_marker = (
        f"{'postgres' + 'ql'}://private-user:{'private-' + 'password'}"
        "@example.invalid/private-db"
    )
    token_marker = "real-admin-token-value"
    confirmation_marker = "real-cloud-confirmation-value"
    webhook_marker = "real-webhook-secret-value"
    private_path_marker = "/Users/private-review/report.md"
    settings = _settings(
        database_url=database_marker,
        admin_token_secret_ref=token_marker,
        secret_provider_cloud_confirmation=confirmation_marker,
        webhook_verification_confirmation_phrase=webhook_marker,
        file_secret_root=private_path_marker,
        procore_api_base="https://private.example.invalid",
    )
    policy = build_infra_security_review_policy(settings)
    assert not hasattr(policy, "database_url")
    assert not hasattr(policy, "admin_token_secret_ref")
    assert not hasattr(policy, "secret_provider_cloud_confirmation")

    report = build_infra_security_review_report(settings)
    with TemporaryDirectory(
        prefix="procore-intake-bridge-infra-security-", dir="/tmp"
    ) as directory:
        write_infra_security_review_artifacts(report, Path(directory))
        rendered = "\n".join(
            (Path(directory) / name).read_text(encoding="utf-8")
            for name in ARTIFACT_FILES
            + ("manifest.json",)
        )
    for marker in (
        database_marker,
        token_marker,
        confirmation_marker,
        webhook_marker,
        private_path_marker,
    ):
        assert marker not in rendered
    assert "postgresql://" not in rendered
    assert "https://" not in rendered
    assert "password=" not in rendered.casefold()
    assert "authorization:" not in rendered.casefold()


@pytest.mark.parametrize(
    "unsafe",
    (
        "token=injected-token",
        "password=injected-password",
        "client_secret=injected-client-secret",
        "webhook_secret=injected-webhook-secret",
        f"{'Authorization'}: {'Bearer'} injected-token",
        f"{'postgres' + 'ql'}://user:{'password'}@example.invalid/db",
        "signed_url=https://example.invalid/signed",
        "storage_key=private-object-key",
        "object_key=private-object-key",
        "-----BEGIN PRIVATE KEY-----",
        "/Users/private/report.md",
        "raw_provider_configuration=injected-value",
    ),
)
def test_prohibited_report_value_is_rejected_before_filesystem_write(tmp_path, unsafe):
    report = build_infra_security_review_report(_settings())
    report.findings = [
        InfraSecurityFinding(
            code="injected_test_value",
            message=unsafe,
        )
    ]
    output = tmp_path / "procore-intake-bridge-infra-security-blocked"
    with pytest.raises(InfraSecurityReviewBlockedError):
        write_infra_security_review_artifacts(report, output)
    assert not output.exists()


def test_cli_and_make_targets_run():
    commands = (
        [".venv/bin/python", "scripts/run_infra_security_review.py"],
        [".venv/bin/python", "scripts/print_secret_boundary_map.py"],
        [".venv/bin/python", "scripts/print_storage_boundary_map.py"],
        [".venv/bin/python", "scripts/print_database_boundary_map.py"],
        [".venv/bin/python", "scripts/print_infra_security_checklist.py"],
        [".venv/bin/python", "scripts/generate_infra_security_review_artifacts.py", "--temporary"],
        ["make", "infra-security-review"],
        ["make", "secret-boundary-map"],
        ["make", "storage-boundary-map"],
        ["make", "database-boundary-map"],
        ["make", "infra-security-checklist"],
        ["make", "infra-security-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr


def test_docs_examples_ignore_and_quality_contracts():
    required = (
        "docs/secrets-storage-db-security-review.md",
        "docs/secret-boundary-map.md",
        "docs/storage-boundary-map.md",
        "docs/database-boundary-map.md",
        "docs/infra-security-checklist.md",
        "examples/infra-security-review/README.md",
        "examples/infra-security-review/example_secret_boundary_map.md",
        "examples/infra-security-review/example_storage_boundary_map.md",
        "examples/infra-security-review/example_database_boundary_map.md",
        "examples/infra-security-review/example_infra_security_checklist.md",
        "examples/infra-security-review/example_infra_provider_matrix.csv",
    )
    assert all((ROOT / path).is_file() for path in required)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(pattern in gitignore for pattern in IGNORED_OUTPUTS)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert (
        "quality: infra-security-review secret-boundary-map storage-boundary-map "
        "database-boundary-map infra-security-checklist"
        in makefile
    )
    assert "quality: infra-security-artifact-check" not in makefile


def test_public_safety_and_route_contracts(tmp_path):
    path = tmp_path / "infra-security-review.md"
    assert audit_text(path, "This review is production-ready.")
    assert audit_text(path, "storage_key=private-value")
    generated = tmp_path / "infra-security-review-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder", encoding="utf-8")
    assert audit_paths([generated])
    routes = application_routes()
    assert len(routes) == 81
    assert not any("DELETE" in (route.methods or set()) for route in routes)
    assert audit_routes() == []

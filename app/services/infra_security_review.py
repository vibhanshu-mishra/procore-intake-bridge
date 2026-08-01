import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.infra_security_review import (
    DatabaseBoundary,
    InfraProviderMatrixItem,
    InfraSecurityArtifactResult,
    InfraSecurityCategory,
    InfraSecurityControl,
    InfraSecurityDecision,
    InfraSecurityFinding,
    InfraSecurityReviewReport,
    InfraSecurityReviewStatus,
    InfraSecurityScenario,
    SecretBoundary,
    StorageBoundary,
)


class InfraSecurityReviewError(ValueError):
    pass


class InfraSecurityReviewBlockedError(InfraSecurityReviewError):
    pass


IGNORED_OUTPUTS = (
    "infra-security-review-output/",
    "secrets-storage-db-review-output/",
    "secret-storage-review-output/",
    "database-security-review-output/",
    "storage-security-review-output/",
    "*.infra-security-review-report.json",
    "*.infra-security-review-report.md",
    "*.secret-boundary-map.md",
    "*.storage-boundary-map.md",
    "*.database-boundary-map.md",
    "*.infra-security-checklist.md",
    "*.infra-provider-matrix.csv",
)
SAFE_ROOTS = {item.rstrip("/") for item in IGNORED_OUTPUTS[:5]}
ARTIFACT_FILES = (
    "infra-security-review-report.json",
    "infra-security-review-report.md",
    "secret-boundary-map.md",
    "storage-boundary-map.md",
    "database-boundary-map.md",
    "infra-security-checklist.md",
    "infra-provider-matrix.csv",
    "manifest.json",
)
EVIDENCE_FILES = (
    "app/security/secret_provider_factory.py",
    "app/security/secrets.py",
    "app/services/secret_inventory.py",
    "app/services/attachment_storage_factory.py",
    "app/services/attachment_storage_provider.py",
    "app/services/attachment_review.py",
    "app/services/database_runtime.py",
    "app/services/database_readiness.py",
    "app/services/migration_status.py",
    "app/services/diagnostic_redaction.py",
    "app/services/private_workspace.py",
    "docs/secret-providers.md",
    "docs/cloud-secret-providers.md",
    "docs/storage-providers.md",
    "docs/cloud-storage-providers.md",
    "docs/postgres-runtime-operations.md",
    "docs/postgres-migration-runbook.md",
    "docs/postgres-backup-restore-drills.md",
    "scripts/audit_public_safety.py",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|sqlite)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\+?\d[\d(). -]{8,}\d")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:token|password|api_key|"
    r"client_secret|webhook_secret|admin_token|signature)\s*[:=]\s*"
    r"(?!false\b|placeholder\b)\S+)"
)
DOMAIN = re.compile(r"(?i)\b[a-z0-9-]+\.(?:com|net|org|io|co)\b")
LONG_ID = re.compile(r"\b(?:\d{12}|[0-9a-f]{8}-[0-9a-f-]{27,})\b", re.I)
CLOUD_ID = re.compile(r"(?i)(?:\barn:aws\S+|/subscriptions/\S+|\bprojects/\S+)")
KEY_MATERIAL = re.compile(
    r"(?i)(?:BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE REQUEST)|"
    r"_acme-challenge|registry\S+:\S+)"
)
PRIVATE_CONTENT = re.compile(
    r"(?i)(?:presigned_url|signed_url|storage_key|object_key|attachment_content|"
    r"db_dump_content|backup_archive_content|migration_log|private_report_contents?)"
    r"\s*[:=]\s*(?!false\b|none\b|placeholder\b)\S+"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa) compliant\b|\b(?:soc ?2|iso ?27001) certified\b|"
    r"\b(?:compliance|security) certified\b|\bproduction[- ]ready\b|"
    r"\b(?:launch|pilot) approved\b|\bprocore (?:endorsed|partner|certified)\b"
)
FORBIDDEN_KEYS = {
    "secret_value",
    "password",
    "api_key",
    "authorization",
    "admin_token",
    "webhook_secret",
    "signature_value",
    "dmsa_client_id",
    "dmsa_client_secret",
    "database_url",
    "source_url",
    "signed_url",
    "presigned_url",
    "storage_key",
    "object_key",
    "private_path",
    "attachment_content",
    "db_dump_content",
    "backup_archive_content",
    "migration_log",
    "report_contents",
}


def sanitize_infra_security_value(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if any(
        pattern.search(text)
        for pattern in (
            URL,
            DB_URL,
            EMAIL,
            PHONE,
            PRIVATE_PATH,
            SECRET,
            DOMAIN,
            LONG_ID,
            CLOUD_ID,
            KEY_MATERIAL,
            PRIVATE_CONTENT,
        )
    ):
        return "[redacted]"
    return text[:400]


def build_infra_security_categories(settings: Settings) -> list[InfraSecurityCategory]:
    return list(InfraSecurityCategory)


def build_secret_boundaries(settings: Settings) -> list[SecretBoundary]:
    return list(SecretBoundary)


def build_storage_boundaries(settings: Settings) -> list[StorageBoundary]:
    return list(StorageBoundary)


def build_database_boundaries(settings: Settings) -> list[DatabaseBoundary]:
    return list(DatabaseBoundary)


def build_infra_security_controls(settings: Settings) -> list[InfraSecurityControl]:
    items = (
        (
            "secret provider registry",
            "app/security/secret_provider_factory.py",
            "References resolve through gated providers.",
        ),
        (
            "secret inventory masking",
            "app/services/secret_inventory.py",
            "Readiness output masks secret material.",
        ),
        (
            "storage provider factory",
            "app/services/attachment_storage_factory.py",
            "Storage providers are selected explicitly.",
        ),
        (
            "attachment metadata",
            "app/services/attachment_review.py",
            "Review remains metadata-only.",
        ),
        (
            "database operation gates",
            "app/services/database_runtime.py",
            "External database operations require explicit gates.",
        ),
        (
            "migration posture",
            "app/services/migration_status.py",
            "Migration status is inspected locally.",
        ),
        (
            "diagnostic masking",
            "app/services/diagnostic_redaction.py",
            "Diagnostics sanitize sensitive values.",
        ),
        (
            "private workspace",
            "app/services/private_workspace.py",
            "Private references stay outside public output.",
        ),
    )
    return [
        InfraSecurityControl(
            name=name, evidence_path=path, description=description, implemented=Path(path).is_file()
        )
        for name, path, description in items
    ]


def build_infra_security_scenarios(settings: Settings) -> list[InfraSecurityScenario]:
    return [
        InfraSecurityScenario(
            category=item,
            expectation=(
                "Review local code and placeholder references without live infrastructure access."
            ),
        )
        for item in InfraSecurityCategory
    ]


def build_infra_provider_matrix(settings: Settings) -> list[InfraProviderMatrixItem]:
    providers = (
        ("environment reference", "secret"),
        ("contained file reference", "secret"),
        ("disabled secret provider", "secret"),
        ("external placeholder", "secret"),
        ("AWS reference", "secret"),
        ("Azure reference", "secret"),
        ("GCP reference", "secret"),
        ("disabled storage", "storage"),
        ("local metadata", "storage"),
        ("test storage", "storage"),
        ("S3 reference", "storage"),
        ("Azure Blob reference", "storage"),
        ("GCS reference", "storage"),
        ("SQLite demo", "database"),
        ("PostgreSQL reference", "database"),
    )
    return [
        InfraProviderMatrixItem(provider=provider, boundary=boundary)
        for provider, boundary in providers
    ]


def build_infra_security_review_report(settings: Settings) -> InfraSecurityReviewReport:
    if not settings.infra_security_review_enabled:
        raise InfraSecurityReviewError("Infrastructure security review is disabled.")
    required = (
        settings.infra_security_review_require_placeholders,
        settings.infra_security_review_require_secret_references,
        settings.infra_security_review_require_no_secret_values,
        settings.infra_security_review_require_secret_masking,
        settings.infra_security_review_require_storage_metadata_only,
        settings.infra_security_review_require_no_presigned_urls,
        settings.infra_security_review_require_no_storage_keys,
        settings.infra_security_review_require_db_url_references,
        settings.infra_security_review_require_db_operation_gates,
        settings.infra_security_review_require_migration_gates,
        settings.infra_security_review_require_backup_restore_plans,
    )
    allowed = (
        settings.infra_security_review_allow_real_identities,
        settings.infra_security_review_allow_real_domains,
        settings.infra_security_review_allow_real_urls,
        settings.infra_security_review_allow_report_contents,
        settings.infra_security_review_allow_private_paths,
    )
    if settings.infra_security_review_fail_closed and (not all(required) or any(allowed)):
        raise InfraSecurityReviewBlockedError("Unsafe infrastructure security policy was blocked.")
    findings = [
        InfraSecurityFinding(
            code="missing_review_evidence",
            message=f"Required local evidence is missing: {path}.",
            severity="blocker",
        )
        for path in EVIDENCE_FILES
        if not Path(path).is_file()
    ]
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    findings.extend(
        InfraSecurityFinding(
            code="missing_ignore_rule",
            message=f"Required generated-output ignore rule is missing: {pattern}.",
            severity="blocker",
        )
        for pattern in IGNORED_OUTPUTS
        if pattern not in gitignore
    )
    findings.extend(
        (
            InfraSecurityFinding(
                code="private_provider_configuration_needs_review",
                message=(
                    "Private provider permissions and resource policies require "
                    "infrastructure review."
                ),
            ),
            InfraSecurityFinding(
                code="live_database_operations_out_of_scope",
                message=(
                    "Connectivity, migration, backup, restore, and dump inspection remain "
                    "separately gated and private."
                ),
            ),
        )
    )
    findings = findings[: settings.infra_security_review_max_findings]
    blockers = [item.message for item in findings if item.severity == "blocker"]
    status = (
        InfraSecurityReviewStatus.BLOCKED
        if blockers
        else InfraSecurityReviewStatus.NEEDS_REVIEW
        if findings
        else InfraSecurityReviewStatus.READY
    )
    decision = {
        InfraSecurityReviewStatus.BLOCKED: InfraSecurityDecision.BLOCKED,
        InfraSecurityReviewStatus.NEEDS_REVIEW: InfraSecurityDecision.NEEDS_REVIEW,
        InfraSecurityReviewStatus.READY: InfraSecurityDecision.READY_FOR_SECURITY_REVIEW,
    }[status]
    categories = build_infra_security_categories(settings)
    secret = build_secret_boundaries(settings)
    storage = build_storage_boundaries(settings)
    database = build_database_boundaries(settings)
    matrix = build_infra_provider_matrix(settings)
    report = InfraSecurityReviewReport(
        status=status,
        decision=decision,
        categories=categories,
        secret_boundaries=secret,
        storage_boundaries=storage,
        database_boundaries=database,
        controls=build_infra_security_controls(settings),
        scenarios=build_infra_security_scenarios(settings),
        provider_matrix=matrix,
        categories_total=len(categories),
        secret_boundaries_total=len(secret),
        storage_boundaries_total=len(storage),
        database_boundaries_total=len(database),
        provider_matrix_items_total=len(matrix),
        findings=findings,
        blockers=blockers,
        warnings=[item.message for item in findings if item.severity != "blocker"],
        recommended_next_steps=[
            "Review provider permissions and resource policies privately.",
            "Exercise database and storage gates only in an authorized private environment.",
            "Treat this offline review as guidance, not certification or production approval.",
        ],
    )
    validate_infra_security_review_report_safe(report)
    return report


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_infra_security_review_report_safe(report: BaseModel | dict[str, Any] | str) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    text = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
    keys = set(_walk_keys(payload)) if not isinstance(payload, str) else set()
    if keys & FORBIDDEN_KEYS or any(
        pattern.search(text)
        for pattern in (
            URL,
            DB_URL,
            EMAIL,
            PHONE,
            PRIVATE_PATH,
            SECRET,
            DOMAIN,
            LONG_ID,
            CLOUD_ID,
            KEY_MATERIAL,
            PRIVATE_CONTENT,
        )
    ):
        raise InfraSecurityReviewBlockedError("Unsafe infrastructure review content was blocked.")
    for line in text.splitlines():
        if UNSAFE_CLAIM.search(line) and not re.search(
            r"(?i)\b(?:no|not|never|does not|is not)\b", line
        ):
            raise InfraSecurityReviewBlockedError("Unsafe infrastructure review claim was blocked.")


def _render_map(title: str, items: list[Any]) -> str:
    rendered = "\n".join(
        [
            f"# {title}",
            "",
            "Offline reference boundary; no live value or operation is included.",
            "",
            *(f"- `{item.value}`" for item in items),
            "",
        ]
    )
    validate_infra_security_review_report_safe(rendered)
    return rendered


def render_infra_security_review_markdown(report: InfraSecurityReviewReport) -> str:
    lines = [
        "# Secrets / Storage / Database Security Review",
        "",
        f"Status: `{report.status.value}`",
        f"Decision: `{report.decision.value}`",
        "",
        "Offline review only. No secret retrieval, storage access, database connection, "
        "migration, backup, restore, dump inspection, external call, or Procore call was "
        "attempted.",
        "",
    ]
    lines.extend(f"- `{item.code}` — {item.message}" for item in report.findings)
    lines.extend(
        [
            "",
            "This review is not legal, compliance, or security certification and is not "
            "production or pilot approval.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_infra_security_review_report_safe(rendered)
    return rendered


def render_secret_boundary_map_markdown(report: InfraSecurityReviewReport) -> str:
    return _render_map("Secret Boundary Map", report.secret_boundaries)


def render_storage_boundary_map_markdown(report: InfraSecurityReviewReport) -> str:
    return _render_map("Storage Boundary Map", report.storage_boundaries)


def render_database_boundary_map_markdown(report: InfraSecurityReviewReport) -> str:
    return _render_map("Database Boundary Map", report.database_boundaries)


def render_infra_security_checklist_markdown(report: InfraSecurityReviewReport) -> str:
    rendered = "\n".join(
        (
            "# Infrastructure Security Checklist",
            "",
            "- [ ] Keep secret and database configuration reference-only.",
            "- [ ] Keep storage review metadata-only; exclude object keys, presigned URLs, "
            "and contents.",
            "- [ ] Keep connectivity, migrations, backups, and restores separately gated.",
            "- [ ] Keep diagnostics masked and generated outputs ignored.",
            "- [ ] Complete private infrastructure and security review.",
            "- [ ] Do not claim certification or production, launch, or pilot approval.",
            "",
        )
    )
    validate_infra_security_review_report_safe(rendered)
    return rendered


def _csv_cell(value: Any) -> str:
    text = sanitize_infra_security_value(value)
    return f"'{text}" if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_infra_provider_matrix_csv(report: InfraSecurityReviewReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        ("provider", "boundary", "enabled_by_default", "external_access", "values_exposed")
    )
    for item in report.provider_matrix:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.provider,
                    item.boundary,
                    str(item.enabled_by_default).lower(),
                    str(item.external_access_attempted).lower(),
                    str(item.values_exposed).lower(),
                )
            )
        )
    rendered = output.getvalue()
    validate_infra_security_review_report_safe(rendered)
    return rendered


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-infra-security-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if ".." in root.parts or (root.is_absolute() and not temporary):
        raise InfraSecurityReviewBlockedError("Unsafe infrastructure review output root.")
    if not temporary and root.parts[:1] not in {(name,) for name in SAFE_ROOTS}:
        raise InfraSecurityReviewBlockedError("Unapproved infrastructure review output root.")
    return root


def write_infra_security_review_artifacts(
    report: InfraSecurityReviewReport, output_root: Path
) -> InfraSecurityArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "infra-security-review-report.json": report.model_dump_json(indent=2),
        "infra-security-review-report.md": render_infra_security_review_markdown(report),
        "secret-boundary-map.md": render_secret_boundary_map_markdown(report),
        "storage-boundary-map.md": render_storage_boundary_map_markdown(report),
        "database-boundary-map.md": render_database_boundary_map_markdown(report),
        "infra-security-checklist.md": render_infra_security_checklist_markdown(report),
        "infra-provider-matrix.csv": render_infra_provider_matrix_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {
            "files": sorted(artifacts),
            "sanitized": True,
            "live_operations": False,
            "secret_retrieval": False,
            "storage_access": False,
            "database_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        validate_infra_security_review_report_safe(content)
        (root / name).write_text(content, encoding="utf-8")
    return InfraSecurityArtifactResult(
        status=report.status, output_directory=root.name, files=sorted(artifacts)
    )

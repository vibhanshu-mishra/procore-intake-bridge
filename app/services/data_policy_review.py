import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.data_policy_review import (
    DataClassification,
    DataPolicyArtifactResult,
    DataPolicyControl,
    DataPolicyDecision,
    DataPolicyFinding,
    DataPolicyReviewReport,
    DataPolicyReviewStatus,
    DataPolicyScenario,
    DataRedactionBoundary,
    DataRetentionBoundary,
    DataRetentionItem,
    GeneratedOutputInventoryItem,
)


class DataPolicyReviewError(ValueError):
    pass


class DataPolicyReviewBlockedError(DataPolicyReviewError):
    pass


IGNORED_OUTPUTS = (
    "data-policy-review-output/",
    "data-retention-redaction-output/",
    "retention-redaction-output/",
    "redaction-review-output/",
    "data-classification-output/",
    "*.data-policy-review-report.json",
    "*.data-policy-review-report.md",
    "*.data-retention-map.md",
    "*.redaction-boundary-map.md",
    "*.generated-output-inventory.csv",
    "*.data-handling-checklist.md",
)
SAFE_ROOTS = {
    "data-policy-review-output",
    "data-retention-redaction-output",
    "retention-redaction-output",
    "redaction-review-output",
    "data-classification-output",
}
ARTIFACT_FILES = (
    "data-policy-review-report.json",
    "data-policy-review-report.md",
    "data-retention-map.md",
    "redaction-boundary-map.md",
    "data-handling-checklist.md",
    "generated-output-inventory.csv",
    "manifest.json",
)
EVIDENCE_FILES = (
    "scripts/audit_public_safety.py",
    "scripts/audit_routes_read_only.py",
    "app/services/diagnostic_redaction.py",
    "app/services/event_queue.py",
    "app/services/attachment_review.py",
    "app/services/operator_export_pack.py",
    "app/services/intake_lifecycle.py",
    "app/services/sandbox_evidence_linkage.py",
    "app/services/private_workspace.py",
    "app/services/secrets.py",
    "app/services/attachment_storage_inventory.py",
    "docs/safety-model.md",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|sqlite)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\+?\d[\d(). -]{8,}\d")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:token|password|client_secret|webhook_secret|signature)\s*[:=]\s*(?!false\b)\S+)"
)
DOMAIN = re.compile(r"(?i)\b[a-z0-9-]+\.(?:com|net|org|io|co)\b")
LONG_ID = re.compile(r"\b(?:\d{12}|[0-9a-f]{8}-[0-9a-f-]{27,})\b", re.I)
CLOUD_ID = re.compile(r"(?i)(?:\barn:aws\S+|/subscriptions/\S+|\bprojects/\S+)")
KEY_MATERIAL = re.compile(
    r"(?i)(?:BEGIN (?:RSA |EC |OPENSSH )?"
    r"(?:PRIVATE KEY|CERTIFICATE REQUEST)|_acme-challenge|registry\S+:\S+)"
)
PRIVATE_CONTENT = re.compile(
    r"(?i)(?:live webhook (?:headers?|payloads?)\s*[:=]|raw_payload\s*[:=]|"
    r"signed_url\s*[:=]|storage_key\s*[:=]|original_filename\s*[:=]|"
    r"attachment_content\s*[:=]|deletion_log\s*[:=]|private report contents?\s*[:=])"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa) compliant\b|"
    r"\b(?:soc ?2|iso ?27001) certified\b|"
    r"\b(?:compliance|security) certified\b|\bproduction[- ]ready\b|"
    r"\b(?:launch|pilot) approved\b|"
    r"\bprocore (?:endorsed|partner|certified|officially supported)\b|"
    r"\bpurge job (?:implemented|enabled|active)\b"
)
FORBIDDEN_KEYS = {
    "raw_payload",
    "raw_headers",
    "source_url",
    "signed_url",
    "database_url",
    "private_path",
    "report_contents",
    "authorization",
    "storage_key",
    "original_filename",
    "attachment_content",
    "deletion_log",
}


def sanitize_data_policy_value(value: Any) -> str:
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


def build_data_classifications(settings: Settings) -> list[DataClassification]:
    return list(DataClassification)


def build_retention_boundaries(settings: Settings) -> list[DataRetentionItem]:
    classifications = {
        DataRetentionBoundary.PUBLIC_REPOSITORY: DataClassification.PUBLIC_PLACEHOLDER,
        DataRetentionBoundary.LOCAL_DEMO_SQLITE: DataClassification.LOCAL_DEMO_METADATA,
        DataRetentionBoundary.LOCAL_POSTGRES_RUNTIME: DataClassification.LOCAL_RUNTIME_METADATA,
        DataRetentionBoundary.WEBHOOK_EVENT_QUEUE: DataClassification.WEBHOOK_PAYLOAD_BOUNDARY,
        DataRetentionBoundary.ATTACHMENT_MANIFEST_METADATA: DataClassification.ATTACHMENT_METADATA,
        DataRetentionBoundary.LIFECYCLE_EVENT_HISTORY: DataClassification.LOCAL_RUNTIME_METADATA,
        DataRetentionBoundary.OPERATOR_EXPORTS: DataClassification.EXPORT_SUMMARY_METADATA,
        DataRetentionBoundary.DIAGNOSTICS_OUTPUT: DataClassification.DIAGNOSTICS_SUMMARY_METADATA,
        DataRetentionBoundary.SUPPORT_BUNDLE_OUTPUT: (
            DataClassification.DIAGNOSTICS_SUMMARY_METADATA
        ),
        DataRetentionBoundary.SANDBOX_EVIDENCE_REFERENCES: (
            DataClassification.PRIVATE_EVIDENCE_REFERENCE
        ),
        DataRetentionBoundary.PILOT_EVIDENCE_WORKSPACE: (
            DataClassification.PRIVATE_EVIDENCE_REFERENCE
        ),
        DataRetentionBoundary.GENERATED_OUTPUT_DIRECTORIES: DataClassification.GENERATED_OUTPUT,
        DataRetentionBoundary.PRIVATE_WORKSPACE: DataClassification.PRIVATE_CONFIGURATION_REFERENCE,
        DataRetentionBoundary.CLOUD_SECRET_REFERENCE_BOUNDARY: DataClassification.SECRET_REFERENCE,
        DataRetentionBoundary.CLOUD_STORAGE_METADATA_BOUNDARY: (
            DataClassification.ATTACHMENT_METADATA
        ),
    }
    private = {
        DataRetentionBoundary.LOCAL_POSTGRES_RUNTIME,
        DataRetentionBoundary.SUPPORT_BUNDLE_OUTPUT,
        DataRetentionBoundary.PILOT_EVIDENCE_WORKSPACE,
        DataRetentionBoundary.PRIVATE_WORKSPACE,
        DataRetentionBoundary.CLOUD_SECRET_REFERENCE_BOUNDARY,
        DataRetentionBoundary.CLOUD_STORAGE_METADATA_BOUNDARY,
    }
    return [
        DataRetentionItem(
            boundary=boundary,
            classification=classifications[boundary],
            public_handling="Placeholder, metadata, or reference-only policy boundary.",
            private_review_required=boundary in private,
        )
        for boundary in DataRetentionBoundary
    ]


def build_redaction_boundaries(settings: Settings) -> list[DataRedactionBoundary]:
    return list(DataRedactionBoundary)


def build_data_policy_controls(settings: Settings) -> list[DataPolicyControl]:
    controls = (
        (
            "public safety audit",
            "scripts/audit_public_safety.py",
            "Generated and sensitive public material is rejected.",
        ),
        (
            "route audit",
            "scripts/audit_routes_read_only.py",
            "Route inventory detects unsafe public surfaces.",
        ),
        (
            "diagnostic sanitization",
            "app/services/diagnostic_redaction.py",
            "Diagnostic values use a shared sanitizer.",
        ),
        (
            "webhook boundary",
            "app/services/event_queue.py",
            "Webhook failures omit submitted details.",
        ),
        (
            "attachment metadata",
            "app/services/attachment_review.py",
            "Attachment review is metadata-only.",
        ),
        (
            "export safety",
            "app/services/operator_export_pack.py",
            "Exports carry public-safety flags and formula neutralization.",
        ),
        (
            "evidence references",
            "app/services/sandbox_evidence_linkage.py",
            "Sandbox evidence stays reference-only.",
        ),
        (
            "private workspace",
            "docs/private-workspace-bootstrap.md",
            "Private material stays outside the public repository.",
        ),
        (
            "secret references",
            "app/services/secrets.py",
            "Provider configuration uses references rather than values.",
        ),
        (
            "storage metadata",
            "app/services/attachment_storage_inventory.py",
            "Storage review is metadata-only.",
        ),
    )
    return [
        DataPolicyControl(
            name=name, evidence_path=path, description=description, implemented=Path(path).is_file()
        )
        for name, path, description in controls
    ]


def build_data_policy_scenarios(settings: Settings) -> list[DataPolicyScenario]:
    retention = list(DataRetentionBoundary)
    redaction = list(DataRedactionBoundary)
    return [
        DataPolicyScenario(
            classification=item,
            retention_boundary=retention[index % len(retention)],
            redaction_boundary=redaction[index % len(redaction)],
            expectation="Review offline with sanitized metadata and references only.",
        )
        for index, item in enumerate(DataClassification)
    ]


def build_generated_output_inventory(settings: Settings) -> list[GeneratedOutputInventoryItem]:
    gitignore = (
        Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").is_file() else ""
    )
    return [
        GeneratedOutputInventoryItem(pattern=pattern, ignored=pattern in gitignore)
        for pattern in IGNORED_OUTPUTS
    ]


def build_data_policy_review_report(settings: Settings) -> DataPolicyReviewReport:
    if not settings.data_policy_review_enabled:
        raise DataPolicyReviewError("Data policy review is disabled.")
    unsafe = any(
        (
            not settings.data_policy_review_require_placeholders,
            not settings.data_policy_review_require_raw_payload_redaction,
            not settings.data_policy_review_require_secret_redaction,
            not settings.data_policy_review_require_url_redaction,
            not settings.data_policy_review_require_path_redaction,
            not settings.data_policy_review_require_attachment_content_exclusion,
            not settings.data_policy_review_require_export_safety_flags,
            not settings.data_policy_review_require_generated_output_ignores,
            settings.data_policy_review_allow_real_identities,
            settings.data_policy_review_allow_real_domains,
            settings.data_policy_review_allow_real_urls,
            settings.data_policy_review_allow_report_contents,
            settings.data_policy_review_allow_private_paths,
        )
    )
    if settings.data_policy_review_fail_closed and unsafe:
        raise DataPolicyReviewBlockedError("Unsafe data policy configuration was blocked.")
    controls = build_data_policy_controls(settings)
    inventory = build_generated_output_inventory(settings)
    findings = [
        DataPolicyFinding(
            code="missing_review_evidence",
            message=f"Required local evidence is missing: {path}.",
            severity="blocker",
        )
        for path in EVIDENCE_FILES
        if not Path(path).is_file()
    ]
    findings.extend(
        DataPolicyFinding(
            code="missing_ignore_rule",
            message=f"Required generated-output ignore rule is missing: {item.pattern}.",
            severity="blocker",
        )
        for item in inventory
        if not item.ignored
    )
    findings.extend(
        (
            DataPolicyFinding(
                code="private_retention_periods_need_review",
                message="Retention periods require private legal and security review.",
            ),
            DataPolicyFinding(
                code="destructive_enforcement_out_of_scope",
                message=(
                    "Persistent-data deletion and purge enforcement are intentionally outside "
                    "this public review."
                ),
            ),
        )
    )
    findings = findings[: settings.data_policy_review_max_findings]
    blockers = [item.message for item in findings if item.severity == "blocker"]
    status = (
        DataPolicyReviewStatus.BLOCKED
        if blockers
        else DataPolicyReviewStatus.NEEDS_REVIEW
        if findings
        else DataPolicyReviewStatus.READY
    )
    decision = {
        DataPolicyReviewStatus.BLOCKED: DataPolicyDecision.BLOCKED,
        DataPolicyReviewStatus.NEEDS_REVIEW: DataPolicyDecision.NEEDS_REVIEW,
        DataPolicyReviewStatus.READY: DataPolicyDecision.READY_FOR_SECURITY_REVIEW,
    }[status]
    classifications = build_data_classifications(settings)
    retention = build_retention_boundaries(settings)
    redaction = build_redaction_boundaries(settings)
    report = DataPolicyReviewReport(
        status=status,
        decision=decision,
        classifications=classifications,
        retention_boundaries=retention,
        redaction_boundaries=redaction,
        controls=controls,
        scenarios=build_data_policy_scenarios(settings),
        generated_output_inventory=inventory,
        classifications_total=len(classifications),
        retention_boundaries_total=len(retention),
        redaction_boundaries_total=len(redaction),
        generated_output_patterns_total=len(inventory),
        findings=findings,
        blockers=blockers,
        warnings=[item.message for item in findings if item.severity != "blocker"],
        recommended_next_steps=[
            "Complete private legal and security review of retention periods.",
            "Define private operational deletion procedures outside this repository.",
            "Keep generated outputs ignored and private workspaces separate.",
            "Treat this policy review as guidance, not legal compliance or approval.",
        ],
    )
    validate_data_policy_review_report_safe(report)
    return report


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_data_policy_review_report_safe(report: BaseModel | dict[str, Any] | str) -> None:
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
        raise DataPolicyReviewBlockedError("Unsafe data policy review content was blocked.")
    for line in text.splitlines():
        if UNSAFE_CLAIM.search(line) and not re.search(
            r"(?i)\b(?:no|not|never|does not|is not)\b", line
        ):
            raise DataPolicyReviewBlockedError("Unsafe data policy claim was blocked.")


def render_data_policy_review_markdown(report: DataPolicyReviewReport) -> str:
    lines = [
        "# Data Retention and Redaction Policy Review",
        "",
        f"Status: `{report.status.value}`",
        f"Decision: `{report.decision.value}`",
        "",
        "Offline repository review only. No live scan, no external call, no Procore call, "
        "no database connection, and no destructive deletion was attempted.",
        "",
    ]
    lines.extend(f"- `{item.code}` — {item.message}" for item in report.findings)
    lines.extend(
        [
            "",
            "This review is not legal compliance certification, production approval, or "
            "pilot approval.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_data_policy_review_report_safe(rendered)
    return rendered


def render_data_retention_map_markdown(report: DataPolicyReviewReport) -> str:
    lines = [
        "# Data Retention Map",
        "",
        "Public outputs contain placeholders, sanitized metadata, or references only.",
        "",
        "| Boundary | Classification | Private review |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| `{item.boundary.value}` | `{item.classification.value}` | "
        f"`{str(item.private_review_required).lower()}` |"
        for item in report.retention_boundaries
    )
    lines.append("")
    rendered = "\n".join(lines)
    validate_data_policy_review_report_safe(rendered)
    return rendered


def render_redaction_boundary_map_markdown(report: DataPolicyReviewReport) -> str:
    lines = [
        "# Redaction Boundary Map",
        "",
        "Excluded values are never copied into public review output.",
        "",
    ]
    lines.extend(
        f"- `{item.value}` — required public-output boundary."
        for item in report.redaction_boundaries
    )
    lines.append("")
    rendered = "\n".join(lines)
    validate_data_policy_review_report_safe(rendered)
    return rendered


def render_data_handling_checklist_markdown(report: DataPolicyReviewReport) -> str:
    rendered = "\n".join(
        (
            "# Data Handling Checklist",
            "",
            "- [ ] Keep public examples placeholder-only.",
            "- [ ] Exclude payloads, headers, secrets, URLs, paths, identifiers, filenames, "
            "and attachment contents.",
            "- [ ] Keep evidence and provider material reference-only.",
            "- [ ] Keep generated outputs ignored.",
            "- [ ] Perform private legal and security review before setting retention periods.",
            "- [ ] Do not add destructive deletion or purge jobs to this public policy layer.",
            "- [ ] Do not claim certification, legal compliance, production approval, or "
            "pilot approval.",
            "",
        )
    )
    validate_data_policy_review_report_safe(rendered)
    return rendered


def _csv_cell(value: Any) -> str:
    text = sanitize_data_policy_value(value)
    return f"'{text}" if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_generated_output_inventory_csv(report: DataPolicyReviewReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("pattern", "classification", "ignored", "content_excluded"))
    for item in report.generated_output_inventory:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.pattern,
                    item.classification.value,
                    str(item.ignored).lower(),
                    str(item.content_excluded).lower(),
                )
            )
        )
    rendered = output.getvalue()
    validate_data_policy_review_report_safe(rendered)
    return rendered


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-data-policy-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if ".." in root.parts or (root.is_absolute() and not temporary):
        raise DataPolicyReviewBlockedError("Unsafe data policy output root.")
    if not temporary and root.parts[:1] not in {(name,) for name in SAFE_ROOTS}:
        raise DataPolicyReviewBlockedError("Unapproved data policy output root.")
    return root


def write_data_policy_review_artifacts(
    report: DataPolicyReviewReport, output_root: Path
) -> DataPolicyArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "data-policy-review-report.json": report.model_dump_json(indent=2),
        "data-policy-review-report.md": render_data_policy_review_markdown(report),
        "data-retention-map.md": render_data_retention_map_markdown(report),
        "redaction-boundary-map.md": render_redaction_boundary_map_markdown(report),
        "data-handling-checklist.md": render_data_handling_checklist_markdown(report),
        "generated-output-inventory.csv": render_generated_output_inventory_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {
            "files": sorted(artifacts),
            "sanitized": True,
            "live_operations": False,
            "deletion_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        validate_data_policy_review_report_safe(content)
        (root / name).write_text(content, encoding="utf-8")
    return DataPolicyArtifactResult(
        status=report.status, output_directory=root.name, files=sorted(artifacts)
    )

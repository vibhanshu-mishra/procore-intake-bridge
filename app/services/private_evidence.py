import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings, get_settings
from app.schemas.private_evidence import (
    EvidenceArtifactResult,
    EvidenceChecklistSection,
    EvidenceItemStatus,
    EvidenceItemType,
    EvidenceManifest,
    EvidenceManifestItem,
    EvidenceRedactionReport,
    EvidenceSensitivityLevel,
    EvidenceValidationFinding,
    EvidenceValidationReport,
)

PLACEHOLDER_MARKERS = ("placeholder", "example", "fake", "sample", "demo")
NUMERIC_ID = re.compile(r"(?<![A-Za-z])\d{4,}(?![A-Za-z])")
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w)")
DOMAIN = re.compile(r"(?i)(?<![\w.-])(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|gov|edu)(?![\w.-])")
SENSITIVE = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|(?:secret|token|password|app[_ ]?version[_ ]?key)"
    r"\s*[:=]\s*\S+)"
)
ENV_ASSIGNMENT = re.compile(r"(?m)^(?:export\s+)?[A-Z][A-Z0-9_]{2,}\s*=\s*\S+")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|sqlite|mongodb)://")
STORAGE_URL = re.compile(r"(?i)\b(?:s3|gs|az|azure|abfs)://|https?://[^/\s]+/(?:bucket|container)/")
SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires|x-amz-signature)=")
ABSOLUTE_PATH = re.compile(r"(?i)(?:^|[\s\"'])(?:/Users/|/home/|/private/|/tmp/|/var/|[A-Z]:\\)")
RAW_REPORT = re.compile(
    r"(?i)(?:raw[_ -]?(?:support bundle|smoke report|webhook report|payload)|"
    r"support[_ -]?bundle[_ -]?contents?|smoke[_ -]?report[_ -]?contents?|"
    r"webhook[_ -]?report[_ -]?contents?)"
)
BINARY_OR_ARTIFACT = re.compile(
    r"(?i)\.(?:db|sqlite|sqlite3|pdf|docx|xlsx|xls|png|jpe?g|gif|webp|zip|tar|gz|"
    r"support-bundle\.json|smoke\.json|webhook-verification\.json|"
    r"evidence-(?:manifest|report|redaction-report)\.json|evidence-(?:index|checklist)\.md)$"
)
SAFE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PrivateEvidenceError(RuntimeError):
    """A sanitized private-evidence planning operation failed."""


class PrivateEvidenceBlockedError(PrivateEvidenceError):
    """A fail-closed safety gate blocked a private-evidence operation."""


def sanitize_evidence_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(term in normalized for term in ("authorization", "raw_payload")) or (
                "contents" in normalized and isinstance(item, (str, list, dict))
            ):
                sanitized[str(key)] = "[redacted]"
            else:
                sanitized[str(key)] = sanitize_evidence_value(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_evidence_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if SENSITIVE.search(value) or ENV_ASSIGNMENT.search(value):
            return "[redacted]"
        if ABSOLUTE_PATH.search(value):
            return "[redacted-path]"
        parsed = urlsplit(value)
        if parsed.scheme and (parsed.query or parsed.username or parsed.password):
            return "[redacted-url]"
    return value


def _placeholder(value: str) -> bool:
    return any(marker in value.casefold() for marker in PLACEHOLDER_MARKERS)


def _finding(
    code: str, message: str, evidence_id: str = "", severity: str = "blocking"
) -> EvidenceValidationFinding:
    return EvidenceValidationFinding(
        code=code, severity=severity, message=message, evidence_id=evidence_id
    )


def _scan_string(value: str) -> set[str]:
    findings = set()
    if NUMERIC_ID.search(value) and not _placeholder(value):
        findings.add("real_id")
    if DOMAIN.search(value) and not _placeholder(value):
        findings.add("domain")
    if EMAIL.search(value):
        findings.add("email")
    if PHONE.search(value):
        findings.add("phone")
    if SENSITIVE.search(value):
        findings.add("secret")
    if SIGNED_URL.search(value):
        findings.add("signed_url")
    if ABSOLUTE_PATH.search(value) or Path(value).is_absolute():
        findings.add("absolute_path")
    if ENV_ASSIGNMENT.search(value):
        findings.add("env_assignment")
    if DB_URL.search(value):
        findings.add("database_url")
    if STORAGE_URL.search(value):
        findings.add("storage_url")
    if RAW_REPORT.search(value):
        findings.add("raw_report")
    if BINARY_OR_ARTIFACT.search(value.strip()):
        findings.add("binary_reference")
    return findings


def _scan_value(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        issues = set()
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in {"payload", "raw_payload", "headers", "records", "file_contents"}:
                issues.add("raw_payload")
            if "contents" in normalized and item not in ("", None, [], {}):
                issues.add("raw_report")
            issues.update(_scan_value(item))
        return issues
    if isinstance(value, (list, tuple)):
        issues = set()
        for item in value:
            issues.update(_scan_value(item))
        return issues
    return _scan_string(value) if isinstance(value, str) else set()


FINDING_MESSAGES = {
    "real_id": "Real-looking numeric identifiers are blocked.",
    "domain": "Real-looking customer domains are blocked.",
    "email": "Email addresses are blocked.",
    "phone": "Phone-like values are blocked.",
    "secret": "Authorization, token, secret, or password material is blocked.",
    "signed_url": "Signed URLs are blocked.",
    "absolute_path": "Absolute local paths are blocked.",
    "env_assignment": "Environment assignments are blocked.",
    "database_url": "Database URLs are blocked.",
    "storage_url": "Storage and bucket URLs are blocked.",
    "raw_payload": "Raw payload-like objects are blocked.",
    "raw_report": "Raw support, smoke, or webhook report contents are blocked.",
    "binary_reference": "Binary or generated private artifact references are blocked.",
}


def validate_evidence_manifest(
    manifest: EvidenceManifest, settings: Settings
) -> list[EvidenceValidationFinding]:
    findings: list[EvidenceValidationFinding] = []
    if not settings.private_evidence_pattern_enabled:
        findings.append(_finding("pattern_disabled", "Private evidence pattern is disabled."))
    if len(manifest.evidence_items) > settings.private_evidence_max_items:
        findings.append(
            _finding("max_items", "Evidence item count exceeds the configured maximum.")
        )
    if manifest.environment.value == "production" and not settings.private_evidence_allow_real_ids:
        findings.append(_finding("production_profile", "Production evidence profiles are blocked."))
    if settings.private_evidence_require_placeholders:
        owner_fields = [manifest.owner_placeholder, manifest.storage_location_placeholder]
        owner_fields.extend(item.owner_placeholder for item in manifest.evidence_items)
        if any(value and not _placeholder(value) for value in owner_fields):
            findings.append(
                _finding(
                    "owner_placeholder",
                    "Owner and location fields must be placeholders.",
                )
            )
    raw = manifest.model_dump(mode="json")
    for code in sorted(_scan_value(raw)):
        if code == "real_id" and settings.private_evidence_allow_real_ids:
            continue
        if code == "absolute_path" and settings.private_evidence_allow_absolute_paths:
            continue
        findings.append(_finding(code, FINDING_MESSAGES[code]))
    for item in manifest.evidence_items:
        if not _placeholder(item.evidence_id):
            findings.append(
                _finding(
                    "evidence_id_placeholder",
                    "Evidence IDs must be placeholders.",
                    item.evidence_id,
                )
            )
        if not _placeholder(item.evidence_ref_placeholder):
            findings.append(
                _finding(
                    "evidence_ref_placeholder",
                    "Evidence references must be placeholders.",
                    item.evidence_id,
                )
            )
        if item.sensitivity != EvidenceSensitivityLevel.PLACEHOLDER:
            findings.append(
                _finding(
                    "sensitivity",
                    "Public templates may use placeholder sensitivity only.",
                    item.evidence_id,
                )
            )
    if not findings:
        findings.append(
            _finding(
                "safe_template",
                "Manifest contains placeholder metadata only.",
                severity="info",
            )
        )
    return findings


def build_evidence_validation_report(
    manifest: EvidenceManifest, settings: Settings
) -> EvidenceValidationReport:
    findings = validate_evidence_manifest(manifest, settings)
    blockers = sum(f.severity == "blocking" for f in findings)
    return EvidenceValidationReport(
        generated_at=datetime.now(UTC),
        workspace_name=manifest.workspace_name,
        environment=manifest.environment.value,
        valid=blockers == 0,
        blocking_findings_count=blockers,
        warning_findings_count=sum(f.severity == "warning" for f in findings),
        item_count=len(manifest.evidence_items),
        findings=findings,
    )


def render_evidence_index(
    manifest: EvidenceManifest, report: EvidenceValidationReport
) -> str:
    lines = [
        "# Private evidence index",
        "",
        "Placeholder metadata only. No evidence files or contents are included.",
        "",
        f"- Workspace: `{manifest.workspace_name}`",
        f"- Environment: `{manifest.environment.value}`",
        f"- Validation: `{'SAFE' if report.valid else 'BLOCKED'}`",
        "",
        "| Evidence ID | Type | Status | Reference placeholder |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| `{item.evidence_id}` | `{item.evidence_type.value}` | `{item.status.value}` | "
        f"`{item.evidence_ref_placeholder}` |"
        for item in manifest.evidence_items
    )
    return "\n".join(lines) + "\n"


def render_evidence_checklist(
    manifest: EvidenceManifest, report: EvidenceValidationReport
) -> str:
    sections = [
        EvidenceChecklistSection(
            title="Workspace safety",
            items=[
                "Keep real evidence outside GitHub.",
                "Store references only in the manifest.",
                "Redact secrets, identities, IDs, paths, URLs, and customer data.",
                "Review access, retention, and reviewer handoff privately.",
            ],
        ),
        EvidenceChecklistSection(
            title="Evidence placeholders",
            items=[
                f"[ ] {item.evidence_type.value}: {item.evidence_ref_placeholder}"
                for item in manifest.evidence_items
            ],
        ),
    ]
    lines = [
        "# Private evidence checklist",
        "",
        f"Validation blockers: {report.blocking_findings_count}",
        "",
    ]
    for section in sections:
        lines.extend(
            [f"## {section.title}", "", *[f"- {item}" for item in section.items], ""]
        )
    return "\n".join(lines)


def _redaction_report(
    manifest: EvidenceManifest, report: EvidenceValidationReport
) -> EvidenceRedactionReport:
    return EvidenceRedactionReport(
        workspace_name=manifest.workspace_name,
        safe_for_local_scaffold=report.valid,
        blocking_findings_count=report.blocking_findings_count,
        redaction_required_count=sum(item.redaction_required for item in manifest.evidence_items),
        excluded_content_categories=[
            "secrets and authorization material",
            "customer identities, domains, and identifiers",
            "absolute paths, URLs, and storage locations",
            "raw payloads, reports, screenshots, logs, and support bundles",
            "database files, attachments, and binary documents",
        ],
    )


def render_evidence_redaction_report(
    manifest: EvidenceManifest, report: EvidenceValidationReport
) -> str:
    payload = _redaction_report(manifest, report).model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_evidence_workspace_readme(
    manifest: EvidenceManifest, report: EvidenceValidationReport
) -> str:
    return (
        "# Private pilot evidence workspace scaffold\n\n"
        "This local scaffold organizes placeholder metadata only. It does not collect, copy, "
        "validate, or contain real evidence.\n\n"
        f"- Workspace: `{manifest.workspace_name}`\n"
        f"- Validation blockers: `{report.blocking_findings_count}`\n"
        "- External calls: `false`\n"
        "- Procore calls: `false`\n"
        "- Evidence file contents included: `false`\n\n"
        "Keep actual evidence in an approved private system outside this public repository. "
        "Share only the minimum redacted material through an authorized review channel.\n"
    )


def build_fake_evidence_template() -> EvidenceManifest:
    items = []
    for index, evidence_type in enumerate(EvidenceItemType, start=1):
        token = evidence_type.value.upper()
        items.append(
            EvidenceManifestItem(
                evidence_id=f"EVIDENCE_PLACEHOLDER_{index:03d}",
                evidence_type=evidence_type,
                title=f"Example {evidence_type.value.replace('_', ' ').title()} Evidence",
                status=EvidenceItemStatus.PLANNED,
                evidence_ref_placeholder=f"PRIVATE_EVIDENCE_REF_PLACEHOLDER_{token}",
                related_gate=f"B9_GATE_PLACEHOLDER_{token}",
                notes=["Fake metadata only; no evidence contents are included."],
                file_expected=evidence_type not in {EvidenceItemType.KNOWN_LIMITATIONS},
            )
        )
    return EvidenceManifest(
        workspace_name="example-pilot-evidence-workspace",
        workspace_label="Example Pilot Evidence Workspace",
        customer_label="Example Customer",
        environment="staging",
        evidence_items=items,
        notes=["Fake placeholders only; real evidence must remain outside the public repository."],
    )


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise PrivateEvidenceBlockedError(
            "Evidence workspace generation blocked: unsafe output root."
        )
    if not output_root.is_absolute() and output_root.parts[0] not in {
        "private-evidence-output",
        "pilot-evidence-output",
        "evidence-output",
    }:
        raise PrivateEvidenceBlockedError(
            "Evidence workspace generation blocked: use a dedicated output root."
        )
    return output_root.resolve()


def write_private_evidence_workspace(
    manifest: EvidenceManifest,
    output_root: Path,
    settings: Settings | None = None,
) -> EvidenceArtifactResult:
    settings = settings or get_settings()
    report = build_evidence_validation_report(manifest, settings)
    if report.blocking_findings_count and settings.private_evidence_fail_closed:
        raise PrivateEvidenceBlockedError(
            "Evidence workspace generation blocked: manifest failed sanitized validation."
        )
    root = _safe_output_root(Path(output_root))
    if not SAFE_NAME.fullmatch(manifest.workspace_name):
        raise PrivateEvidenceBlockedError(
            "Evidence workspace generation blocked: unsafe workspace name."
        )
    target = (root / manifest.workspace_name).resolve()
    if target.parent != root:
        raise PrivateEvidenceBlockedError("Evidence workspace generation blocked: path traversal.")
    target.mkdir(parents=True, exist_ok=False)
    safe_manifest = sanitize_evidence_value(manifest.model_dump(mode="json"))
    artifact_manifest = {
        "workspace_name": manifest.workspace_name,
        "files": [
            "README.md",
            "evidence-manifest.template.json",
            "evidence-index.md",
            "evidence-checklist.md",
            "evidence-redaction-report.json",
            "manifest.json",
        ],
        "local_only": True,
        "external_calls": False,
        "file_contents_included": False,
    }
    files = {
        "README.md": render_evidence_workspace_readme(manifest, report),
        "evidence-manifest.template.json": (
            json.dumps(safe_manifest, indent=2, sort_keys=True) + "\n"
        ),
        "evidence-index.md": render_evidence_index(manifest, report),
        "evidence-checklist.md": render_evidence_checklist(manifest, report),
        "evidence-redaction-report.json": render_evidence_redaction_report(manifest, report),
        "manifest.json": json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
    }
    for name, content in files.items():
        (target / name).write_text(content, encoding="utf-8")
    return EvidenceArtifactResult(
        workspace_name=manifest.workspace_name,
        output_directory=manifest.workspace_name,
        files=list(files),
    )

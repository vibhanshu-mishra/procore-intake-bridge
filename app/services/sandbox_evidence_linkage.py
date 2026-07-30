from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.schemas.sandbox_evidence_linkage import (
    SandboxEvidenceArtifactResult,
    SandboxEvidenceFinding,
    SandboxEvidenceLinkageProfile,
    SandboxEvidenceLinkageReport,
    SandboxEvidencePilotMapping,
    SandboxEvidenceRef,
    SandboxEvidenceStatus,
    SandboxEvidenceType,
)

PLACEHOLDER_MARKERS = ("placeholder", "example", "fake", "sample", "demo")
SAFE_PROFILE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w)")
URL = re.compile(r"(?i)\b(?:https?|s3|gs|az|abfs)://")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|mongodb|sqlite)://")
DOMAIN = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|gov|edu)\b")
LONG_ID = re.compile(r"(?<![A-Za-z])\d{4,}(?![A-Za-z])")
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
AUTHORIZATION = re.compile(
    r"(?i)(?:authorization\s*:\s*bearer|bearer\s+[a-z0-9._-]+|"
    r"(?:secret|token|password|app[_ ]?version[_ ]?key)\s*[:=]\s*\S+)"
)
PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE)-----"
)
RAW_CONTENT = re.compile(
    r"(?i)(?:raw[_ -]?(?:payload|response|record|report)|"
    r"(?:smoke|sandbox[_ -]?read|webhook)[_ -]?report[_ -]?contents?|"
    r"[\"'](?:subject|title|description|vendor|attachments?|filename|records|payload)"
    r"[\"']\s*:)"
)
PRIVATE_ARTIFACT = re.compile(
    r"(?i)(?:sandbox-smoke-\S+\.smoke\.json|sandbox-read-report\.(?:json|md)|"
    r"sandbox-read-evidence\.(?:json|md)|support-bundle|webhook-report)"
)
APPROVAL_CLAIM = re.compile(
    r"(?i)(?:pilot (?:is )?approved|approval (?:is )?granted|"
    r"evidence (?:equals|proves|grants|creates) approval)"
)
CLOUD_CREDENTIAL = re.compile(
    r"(?i)(?:private_key_id|private_key|client_email|aws_access_key_id|"
    r"aws_secret_access_key)\s*[:=]"
)
ARTIFACT_NAMES = [
    "sandbox-evidence-linkage-report.json",
    "sandbox-evidence-summary.md",
    "evidence-manifest-patch.md",
    "pilot-readiness-mapping.md",
    "pilot-approval-mapping.md",
    "sandbox-to-pilot-flow-mapping.md",
    "manifest.json",
]
SAFE_OUTPUT_NAMES = {
    "sandbox-evidence-output",
    "sandbox-evidence-linkage-output",
    "evidence-linkage-output",
}


class SandboxEvidenceLinkageError(RuntimeError):
    """A sanitized evidence-linkage operation failed."""


class SandboxEvidenceLinkageBlockedError(SandboxEvidenceLinkageError):
    """A fail-closed public-safety rule blocked evidence linkage."""


def _placeholder(value: str) -> bool:
    return any(marker in value.casefold() for marker in PLACEHOLDER_MARKERS)


def sanitize_sandbox_evidence_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(
                term in normalized
                for term in (
                    "authorization",
                    "contents",
                    "payload",
                    "record",
                    "secret",
                    "token",
                )
            ):
                result[str(key)] = "[omitted]"
            else:
                result[str(key)] = sanitize_sandbox_evidence_value(item)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [sanitize_sandbox_evidence_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str) and any(
        pattern.search(value)
        for pattern in (
            EMAIL,
            PHONE,
            URL,
            DB_URL,
            ABSOLUTE_PATH,
            AUTHORIZATION,
            PRIVATE_KEY,
            RAW_CONTENT,
            CLOUD_CREDENTIAL,
        )
    ):
        return "[omitted]"
    return value


def _scan_string(value: str) -> set[str]:
    issues: set[str] = set()
    if URL.search(value):
        issues.add("url")
    if DB_URL.search(value):
        issues.add("database_url")
    if DOMAIN.search(value) and not _placeholder(value):
        issues.add("domain")
    if EMAIL.search(value):
        issues.add("email")
    if PHONE.search(value):
        issues.add("phone")
    if LONG_ID.search(value) and not _placeholder(value):
        issues.add("real_id")
    if ABSOLUTE_PATH.search(value) or Path(value).is_absolute():
        issues.add("absolute_path")
    if AUTHORIZATION.search(value):
        issues.add("authorization")
    if PRIVATE_KEY.search(value):
        issues.add("private_key")
    if CLOUD_CREDENTIAL.search(value):
        issues.add("cloud_credential")
    if RAW_CONTENT.search(value):
        issues.add("report_contents")
    if PRIVATE_ARTIFACT.search(value):
        issues.add("private_artifact")
    if APPROVAL_CLAIM.search(value):
        issues.add("approval_claim")
    if value.strip().startswith(("{", "[")) and any(
        marker in value.casefold()
        for marker in ('"id"', '"subject"', '"title"', '"records"', '"payload"')
    ):
        issues.add("live_record")
    return issues


def _scan_value(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        issues: set[str] = set()
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in {
                "payload",
                "records",
                "raw_payload",
                "report_contents",
                "response_body",
            } and item not in (None, "", [], {}, False):
                issues.add("report_contents")
            issues.update(_scan_value(item))
        return issues
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        issues: set[str] = set()
        for item in value:
            issues.update(_scan_value(item))
        return issues
    return _scan_string(value) if isinstance(value, str) else set()


FINDING_MESSAGES = {
    "url": "URLs are blocked in public evidence linkage.",
    "database_url": "Database URLs are blocked.",
    "domain": "Real-looking domains are blocked.",
    "email": "Email addresses are blocked.",
    "phone": "Phone-like values are blocked.",
    "real_id": "Real-looking numeric identifiers are blocked.",
    "absolute_path": "Absolute private paths are blocked.",
    "authorization": "Authorization, token, or secret material is blocked.",
    "private_key": "Certificate or private-key contents are blocked.",
    "cloud_credential": "Cloud credential material is blocked.",
    "report_contents": "Raw report or response contents are blocked.",
    "private_artifact": "Generated private report filenames are blocked.",
    "approval_claim": "Evidence linkage cannot claim pilot approval.",
    "live_record": "Live response-like JSON records are blocked.",
}


def _finding(code: str, message: str | None = None) -> SandboxEvidenceFinding:
    return SandboxEvidenceFinding(
        code=code,
        status=SandboxEvidenceStatus.BLOCKED,
        message=message or FINDING_MESSAGES[code],
        blocking=True,
    )


def validate_sandbox_evidence_ref(
    ref: SandboxEvidenceRef,
    settings: Settings,
) -> list[SandboxEvidenceFinding]:
    findings = [_finding(code) for code in sorted(_scan_value(ref.model_dump(mode="json")))]
    if settings.sandbox_evidence_linkage_require_placeholders and not _placeholder(
        ref.evidence_ref
    ):
        findings.append(
            _finding("reference_placeholder", "Evidence references must be placeholders.")
        )
    if ref.report_contents_included:
        findings.append(_finding("report_contents"))
    return findings


def validate_sandbox_evidence_profile(
    profile: SandboxEvidenceLinkageProfile,
    settings: Settings,
) -> list[SandboxEvidenceFinding]:
    findings: list[SandboxEvidenceFinding] = []
    if not settings.sandbox_evidence_linkage_enabled:
        findings.append(_finding("linkage_disabled", "Sandbox evidence linkage is disabled."))
    if not settings.sandbox_evidence_linkage_fail_closed:
        findings.append(_finding("fail_open", "Sandbox evidence linkage must fail closed."))
    if len(profile.evidence_refs) > settings.sandbox_evidence_linkage_max_refs:
        findings.append(_finding("too_many_refs", "Evidence reference count exceeds the cap."))
    if not SAFE_PROFILE_NAME.fullmatch(profile.profile_name):
        findings.append(_finding("profile_name", "Profile name must be a safe lowercase slug."))
    for ref in profile.evidence_refs:
        findings.extend(validate_sandbox_evidence_ref(ref, settings))
    placeholder_fields = (
        profile.sandbox_smoke_ref,
        profile.sandbox_read_validation_ref,
        profile.permission_review_ref,
        profile.webhook_review_ref,
        profile.scope_review_ref,
        profile.operator_review_ref,
        profile.reviewer_placeholder,
        profile.expiry_placeholder,
        profile.renewal_placeholder,
    )
    if settings.sandbox_evidence_linkage_require_placeholders and any(
        not _placeholder(value) for value in placeholder_fields if value
    ):
        findings.append(
            _finding(
                "profile_placeholders",
                "Profile references and identities must be placeholders.",
            )
        )
    raw = profile.model_dump(mode="json")
    for code in sorted(_scan_value(raw)):
        if code == "real_id" and settings.sandbox_evidence_linkage_allow_real_ids:
            continue
        if code == "domain" and settings.sandbox_evidence_linkage_allow_real_domains:
            continue
        if code == "absolute_path" and settings.sandbox_evidence_linkage_allow_absolute_paths:
            continue
        if code == "report_contents" and settings.sandbox_evidence_linkage_allow_report_contents:
            continue
        findings.append(_finding(code))
    unique: dict[tuple[str, str], SandboxEvidenceFinding] = {}
    for finding in findings:
        unique[(finding.code, finding.message)] = finding
    return list(unique.values())


def _mapping(
    workflow: str,
    refs: list[str],
    placeholder: str,
) -> SandboxEvidencePilotMapping:
    return SandboxEvidencePilotMapping(
        workflow=workflow,
        reference_placeholders=refs,
        mapping_placeholder=placeholder,
    )


def build_sandbox_evidence_linkage_report(
    profile: SandboxEvidenceLinkageProfile,
    settings: Settings,
) -> SandboxEvidenceLinkageReport:
    findings = validate_sandbox_evidence_profile(profile, settings)
    required = bool(profile.sandbox_smoke_ref and profile.sandbox_read_validation_ref)
    missing = not required or any(
        ref.status == SandboxEvidenceStatus.MISSING for ref in profile.evidence_refs
    )
    status = (
        SandboxEvidenceStatus.BLOCKED
        if any(item.blocking for item in findings)
        else (
            SandboxEvidenceStatus.NEEDS_REVIEW
            if missing
            else SandboxEvidenceStatus.ACCEPTED_PLACEHOLDER
        )
    )
    common_refs = [
        profile.sandbox_smoke_ref,
        profile.sandbox_read_validation_ref,
        profile.permission_review_ref,
        profile.scope_review_ref,
    ]
    report = SandboxEvidenceLinkageReport(
        generated_at=datetime.now(UTC),
        profile_name=profile.profile_name,
        status=status,
        refs_total=len(profile.evidence_refs),
        required_refs_present=required,
        pilot_readiness_mapping=_mapping(
            "pilot_readiness",
            common_refs,
            "PILOT_READINESS_MAPPING_PLACEHOLDER",
        ),
        approval_packet_mapping=_mapping(
            "pilot_approval_packet",
            common_refs,
            "PILOT_APPROVAL_MAPPING_PLACEHOLDER",
        ),
        flow_mapping=_mapping(
            "sandbox_to_pilot_flow",
            common_refs,
            "SANDBOX_TO_PILOT_FLOW_MAPPING_PLACEHOLDER",
        ),
        evidence_review_mapping=_mapping(
            "evidence_review_and_expiry",
            common_refs,
            "EVIDENCE_REVIEW_MAPPING_PLACEHOLDER",
        ),
        findings=findings,
        recommended_next_steps=[
            "Keep source reports and real references in the approved private system.",
            "Require human review, expiry, and renewal before Pilot use.",
            "Treat every mapping as reference metadata, never approval.",
        ],
    )
    validate_sandbox_evidence_report_safe(report)
    return report


def build_default_sandbox_evidence_profile(
    settings: Settings,
) -> SandboxEvidenceLinkageProfile:
    refs = [
        SandboxEvidenceRef(
            evidence_type=evidence_type,
            evidence_ref=placeholder,
        )
        for evidence_type, placeholder in (
            (SandboxEvidenceType.SANDBOX_SMOKE, "SANDBOX_SMOKE_REF_PLACEHOLDER"),
            (
                SandboxEvidenceType.SANDBOX_READ_VALIDATION,
                "SANDBOX_READ_VALIDATION_REF_PLACEHOLDER",
            ),
            (
                SandboxEvidenceType.SANDBOX_PERMISSIONS_REVIEW,
                "SANDBOX_PERMISSION_REVIEW_REF_PLACEHOLDER",
            ),
            (
                SandboxEvidenceType.SANDBOX_WEBHOOK_REVIEW,
                "SANDBOX_WEBHOOK_REVIEW_REF_PLACEHOLDER",
            ),
            (
                SandboxEvidenceType.SANDBOX_SCOPE_REVIEW,
                "SANDBOX_SCOPE_REVIEW_REF_PLACEHOLDER",
            ),
            (
                SandboxEvidenceType.SANDBOX_OPERATOR_REVIEW,
                "SANDBOX_OPERATOR_REVIEW_REF_PLACEHOLDER",
            ),
        )
    ]
    return SandboxEvidenceLinkageProfile(
        profile_name="example-sandbox-evidence-linkage",
        evidence_refs=refs,
        known_limitations=[
            "EXAMPLE_LIMITATION_PLACEHOLDER: human review and expiry remain required."
        ],
        notes=[
            "Fake placeholder references only; evidence linkage does not approve a pilot."
        ],
    )


def render_sandbox_evidence_linkage_markdown(
    report: SandboxEvidenceLinkageReport,
) -> str:
    return (
        "# Sandbox evidence linkage summary\n\n"
        f"- Status: `{report.status.value}`\n"
        f"- Placeholder refs: `{report.refs_total}`\n"
        f"- Required refs present: `{str(report.required_refs_present).lower()}`\n"
        "- Source report contents read: `false`\n"
        "- Pilot approved: `false`\n\n"
        "Mappings require private human review, expiry, and renewal. Evidence linkage does not "
        "prove or grant pilot approval.\n"
    )


def render_sandbox_evidence_manifest_patch(
    profile: SandboxEvidenceLinkageProfile,
    report: SandboxEvidenceLinkageReport,
) -> str:
    return (
        "# Evidence manifest patch template\n\n"
        f"- Sandbox smoke: `{profile.sandbox_smoke_ref}`\n"
        f"- Sandbox read validation: `{profile.sandbox_read_validation_ref}`\n"
        f"- Reviewer: `{profile.reviewer_placeholder}`\n"
        f"- Expiry: `{profile.expiry_placeholder}`\n"
        f"- Renewal: `{profile.renewal_placeholder}`\n\n"
        "Opaque placeholders only. No source report contents are included.\n"
    )


def render_pilot_readiness_mapping(
    profile: SandboxEvidenceLinkageProfile,
    report: SandboxEvidenceLinkageReport,
) -> str:
    return _render_mapping(report.pilot_readiness_mapping)


def render_pilot_approval_mapping(
    profile: SandboxEvidenceLinkageProfile,
    report: SandboxEvidenceLinkageReport,
) -> str:
    return _render_mapping(report.approval_packet_mapping)


def render_flow_mapping(
    profile: SandboxEvidenceLinkageProfile,
    report: SandboxEvidenceLinkageReport,
) -> str:
    return _render_mapping(report.flow_mapping)


def _render_mapping(mapping: SandboxEvidencePilotMapping) -> str:
    lines = [
        f"# {mapping.workflow.replace('_', ' ').title()} mapping",
        "",
        f"- Mapping: `{mapping.mapping_placeholder}`",
        "- Human review required: `true`",
        "- Approval granted: `false`",
        "- Report contents included: `false`",
        "",
        "Reference placeholders:",
        *(f"- `{ref}`" for ref in mapping.reference_placeholders),
    ]
    return "\n".join(lines) + "\n"


def validate_sandbox_evidence_report_safe(
    report: SandboxEvidenceLinkageReport,
) -> None:
    if any(
        (
            report.secrets_exposed,
            report.ids_exposed,
            report.private_paths_exposed,
            report.report_contents_exposed,
            report.external_calls,
            report.procore_calls,
            report.private_evidence_read,
            report.pilot_approved,
        )
    ):
        raise SandboxEvidenceLinkageError("Unsafe sandbox evidence linkage report.")
    serialized = report.model_dump_json()
    if any(
        pattern.search(serialized)
        for pattern in (
            EMAIL,
            PHONE,
            URL,
            DB_URL,
            ABSOLUTE_PATH,
            AUTHORIZATION,
            PRIVATE_KEY,
            CLOUD_CREDENTIAL,
        )
    ):
        raise SandboxEvidenceLinkageError("Unsafe sandbox evidence linkage report content.")


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path(".."), Path("/")} or ".." in output_root.parts:
        raise SandboxEvidenceLinkageBlockedError("Evidence linkage output root is unsafe.")
    if not output_root.is_absolute() and output_root.name not in SAFE_OUTPUT_NAMES:
        raise SandboxEvidenceLinkageBlockedError(
            "Use a dedicated ignored evidence-linkage output root."
        )
    return output_root


def write_sandbox_evidence_linkage_artifacts(
    profile: SandboxEvidenceLinkageProfile,
    output_root: Path,
    settings: Settings | None = None,
) -> SandboxEvidenceArtifactResult:
    resolved = settings or get_settings()
    report = build_sandbox_evidence_linkage_report(profile, resolved)
    if report.status == SandboxEvidenceStatus.BLOCKED:
        raise SandboxEvidenceLinkageBlockedError(
            "Evidence linkage generation blocked by public-safety findings."
        )
    root = _safe_output_root(output_root) / profile.profile_name
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "sandbox-evidence-linkage-report.json": report.model_dump_json(indent=2) + "\n",
        "sandbox-evidence-summary.md": render_sandbox_evidence_linkage_markdown(report),
        "evidence-manifest-patch.md": render_sandbox_evidence_manifest_patch(profile, report),
        "pilot-readiness-mapping.md": render_pilot_readiness_mapping(profile, report),
        "pilot-approval-mapping.md": render_pilot_approval_mapping(profile, report),
        "sandbox-to-pilot-flow-mapping.md": render_flow_mapping(profile, report),
        "manifest.json": json.dumps(
            {
                "profile_name": profile.profile_name,
                "files": ARTIFACT_NAMES[:-1],
                "external_calls": False,
                "procore_calls": False,
                "private_evidence_read": False,
                "pilot_approved": False,
            },
            indent=2,
        )
        + "\n",
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    return SandboxEvidenceArtifactResult(
        profile_name=profile.profile_name,
        output_directory=profile.profile_name,
        files=ARTIFACT_NAMES,
    )

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings, get_settings
from app.schemas.evidence_review import (
    EvidenceExpiryStatus,
    EvidenceRenewalChecklistSection,
    EvidenceReviewArtifactResult,
    EvidenceReviewDecision,
    EvidenceReviewFinding,
    EvidenceReviewGateResult,
    EvidenceReviewItem,
    EvidenceReviewManifest,
    EvidenceReviewReport,
    EvidenceReviewStatus,
    EvidenceReviewSummary,
)
from app.schemas.private_evidence import EvidenceItemType

PLACEHOLDER_MARKERS = ("placeholder", "example", "fake", "sample", "demo")
NUMERIC_ID = re.compile(r"(?<![A-Za-z])\d{4,}(?![A-Za-z])")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T[\d:.+-]+Z?)?$")
PERSON_NAME = re.compile(r"^[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+$")
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w)")
DOMAIN = re.compile(r"(?i)(?<![\w.-])(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|gov|edu)(?![\w.-])")
SENSITIVE = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|(?:secret|token|password|signature|"
    r"app[_ ]?version[_ ]?key)\s*[:=]\s*\S+)"
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
    r"evidence-(?:review|expiry-report)\.json|evidence-review\.md|"
    r"evidence-renewal-checklist\.md|evidence-signoff\.md|reviewer-signoff\.json)$"
)
SAFE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class EvidenceReviewError(RuntimeError):
    """A sanitized local evidence-review operation failed."""


class EvidenceReviewBlockedError(EvidenceReviewError):
    """A fail-closed review safety gate blocked execution."""


def sanitize_evidence_review_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(term in normalized for term in ("authorization", "raw_payload")) or (
                "contents" in normalized and isinstance(item, (str, list, dict))
            ):
                sanitized[str(key)] = "[redacted]"
            else:
                sanitized[str(key)] = sanitize_evidence_review_value(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_evidence_review_value(item) for item in value]
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


def parse_placeholder_date(value: str) -> datetime | None:
    candidate = value.strip()
    if not candidate or any(marker in candidate.casefold() for marker in PLACEHOLDER_MARKERS):
        return None
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)


def calculate_expiry_status(
    reviewed_at: str,
    expires_at: str,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> EvidenceExpiryStatus:
    reviewed = parse_placeholder_date(reviewed_at)
    expires = parse_placeholder_date(expires_at)
    if reviewed is None or expires is None:
        return EvidenceExpiryStatus.NEEDS_REVIEW
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    if expires <= current_time:
        return EvidenceExpiryStatus.EXPIRED
    if expires - current_time <= timedelta(days=settings.evidence_review_warn_within_days):
        return EvidenceExpiryStatus.EXPIRES_SOON
    return EvidenceExpiryStatus.CURRENT


def _placeholder(value: str) -> bool:
    return any(marker in value.casefold() for marker in PLACEHOLDER_MARKERS)


def _finding(
    code: str,
    message: str,
    evidence_id: str = "",
    severity: str = "blocking",
) -> EvidenceReviewFinding:
    return EvidenceReviewFinding(
        code=code, severity=severity, message=message, evidence_id=evidence_id
    )


def _scan_string(value: str) -> set[str]:
    findings = set()
    if NUMERIC_ID.search(value) and not _placeholder(value) and not ISO_DATE.fullmatch(value):
        findings.add("real_id")
    if PERSON_NAME.fullmatch(value.strip()) and not _placeholder(value):
        findings.add("real_identity")
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
    "real_identity": "Real-looking reviewer or approver identities are blocked.",
    "domain": "Real-looking customer domains are blocked.",
    "email": "Email addresses are blocked.",
    "phone": "Phone-like values are blocked.",
    "secret": "Authorization, token, secret, password, or signature material is blocked.",
    "signed_url": "Signed URLs are blocked.",
    "absolute_path": "Absolute local paths are blocked.",
    "env_assignment": "Environment assignments are blocked.",
    "database_url": "Database URLs are blocked.",
    "storage_url": "Storage and bucket URLs are blocked.",
    "raw_payload": "Raw payload-like objects are blocked.",
    "raw_report": "Raw support, smoke, or webhook report contents are blocked.",
    "binary_reference": "Binary or generated private artifact references are blocked.",
}


def _effective_expiry(item: EvidenceReviewItem, settings: Settings) -> EvidenceExpiryStatus:
    if item.review_status == EvidenceReviewStatus.NOT_APPLICABLE:
        return EvidenceExpiryStatus.NOT_APPLICABLE
    if item.renewal_required:
        return EvidenceExpiryStatus.RENEWAL_REQUIRED
    calculated = calculate_expiry_status(
        item.reviewed_at_placeholder, item.expires_at_placeholder, settings
    )
    if calculated == EvidenceExpiryStatus.NEEDS_REVIEW:
        return item.expiry_status
    return calculated


def validate_evidence_review_manifest(
    manifest: EvidenceReviewManifest, settings: Settings
) -> list[EvidenceReviewFinding]:
    findings: list[EvidenceReviewFinding] = []
    if not settings.evidence_review_enabled:
        findings.append(_finding("review_disabled", "Evidence review workflow is disabled."))
    if len(manifest.review_items) > settings.evidence_review_max_items:
        findings.append(_finding("max_items", "Review item count exceeds the configured maximum."))
    if manifest.environment.value == "production" and (
        not settings.evidence_review_allow_real_ids
        or not settings.evidence_review_allow_real_identities
    ):
        findings.append(_finding("production_profile", "Production review profiles are blocked."))
    if settings.evidence_review_require_placeholders:
        identity_values = [manifest.review_owner_placeholder]
        for item in manifest.review_items:
            identity_values.extend(
                [
                    item.reviewer_placeholder.reviewer_placeholder,
                    item.reviewer_placeholder.approver_placeholder,
                    item.reviewer_placeholder.signoff_placeholder,
                ]
            )
        if any(value and not _placeholder(value) for value in identity_values):
            findings.append(
                _finding(
                    "identity_placeholder",
                    "Reviewer and signoff fields must be placeholders.",
                )
            )
    for code in sorted(_scan_value(manifest.model_dump(mode="json"))):
        if code == "real_id" and settings.evidence_review_allow_real_ids:
            continue
        if code == "real_identity" and settings.evidence_review_allow_real_identities:
            continue
        if code == "absolute_path" and settings.evidence_review_allow_absolute_paths:
            continue
        findings.append(_finding(code, FINDING_MESSAGES[code]))
    for item in manifest.review_items:
        reviewed = parse_placeholder_date(item.reviewed_at_placeholder)
        expires = parse_placeholder_date(item.expires_at_placeholder)
        if reviewed and expires:
            if expires < reviewed:
                findings.append(
                    _finding("expiry_order", "Expiry precedes review time.", item.evidence_id)
                )
            elif expires - reviewed > timedelta(days=settings.evidence_review_max_expiry_days):
                findings.append(
                    _finding(
                        "expiry_window",
                        "Expiry window exceeds the configured maximum.",
                        item.evidence_id,
                    )
                )
        if item.review_status == EvidenceReviewStatus.ACCEPTED_PLACEHOLDER:
            if not item.reviewed_at_placeholder.strip():
                findings.append(
                    _finding(
                        "accepted_review_time",
                        "Accepted evidence needs a review timestamp placeholder.",
                        item.evidence_id,
                    )
                )
            if not item.expires_at_placeholder.strip():
                findings.append(
                    _finding(
                        "accepted_expiry_time",
                        "Accepted evidence needs an expiry timestamp placeholder.",
                        item.evidence_id,
                    )
                )
            if (
                _effective_expiry(item, settings) == EvidenceExpiryStatus.EXPIRED
                and not item.renewal_required
            ):
                findings.append(
                    _finding(
                        "expired_accepted",
                        "Expired accepted evidence must require renewal.",
                        item.evidence_id,
                    )
                )
    if not findings:
        findings.append(
            _finding(
                "safe_review",
                "Review manifest contains placeholder metadata only.",
                severity="info",
            )
        )
    return findings


def build_evidence_review_report(
    manifest: EvidenceReviewManifest, settings: Settings
) -> EvidenceReviewReport:
    findings = validate_evidence_review_manifest(manifest, settings)
    gates = []
    for item in manifest.review_items:
        expiry = _effective_expiry(item, settings)
        blocks = item.required_for_gate and (
            item.review_status
            in {
                EvidenceReviewStatus.NOT_STARTED,
                EvidenceReviewStatus.NEEDS_REVIEW,
                EvidenceReviewStatus.REJECTED_PLACEHOLDER,
                EvidenceReviewStatus.BLOCKED,
            }
            or expiry
            in {
                EvidenceExpiryStatus.EXPIRED,
                EvidenceExpiryStatus.RENEWAL_REQUIRED,
                EvidenceExpiryStatus.BLOCKED,
            }
        )
        gates.append(
            EvidenceReviewGateResult(
                evidence_id=item.evidence_id,
                evidence_type=item.evidence_type.value,
                review_status=item.review_status,
                expiry_status=expiry,
                renewal_required=item.renewal_required,
                blocks_gate=blocks,
            )
        )
    summary = EvidenceReviewSummary(
        total_items=len(gates),
        current_items=sum(g.expiry_status == EvidenceExpiryStatus.CURRENT for g in gates),
        needs_review_items=sum(
            g.review_status in {EvidenceReviewStatus.NOT_STARTED, EvidenceReviewStatus.NEEDS_REVIEW}
            or g.expiry_status == EvidenceExpiryStatus.NEEDS_REVIEW
            for g in gates
        ),
        expires_soon_items=sum(g.expiry_status == EvidenceExpiryStatus.EXPIRES_SOON for g in gates),
        expired_items=sum(g.expiry_status == EvidenceExpiryStatus.EXPIRED for g in gates),
        renewal_required_items=sum(
            g.renewal_required or g.expiry_status == EvidenceExpiryStatus.RENEWAL_REQUIRED
            for g in gates
        ),
        blocked_items=sum(g.blocks_gate for g in gates),
    )
    blockers = sum(f.severity == "blocking" for f in findings)
    return EvidenceReviewReport(
        generated_at=datetime.now(UTC),
        profile_name=manifest.profile_name,
        environment=manifest.environment.value,
        valid=blockers == 0,
        blocking_findings_count=blockers,
        warning_findings_count=sum(f.severity == "warning" for f in findings),
        findings=findings,
        gates=gates,
        summary=summary,
    )


def render_evidence_review_summary(
    manifest: EvidenceReviewManifest, report: EvidenceReviewReport
) -> str:
    return (
        "# Evidence review summary\n\n"
        "Placeholder metadata only; no real review or signoff is recorded.\n\n"
        f"- Profile: `{manifest.profile_name}`\n"
        f"- Validation blockers: `{report.blocking_findings_count}`\n"
        f"- Items needing review: `{report.summary.needs_review_items}`\n"
        f"- Items expiring soon: `{report.summary.expires_soon_items}`\n"
        f"- Renewal required: `{report.summary.renewal_required_items}`\n"
        "- External calls: `false`\n"
        "- Notifications sent: `false`\n"
    )


def render_evidence_renewal_checklist(
    manifest: EvidenceReviewManifest, report: EvidenceReviewReport
) -> str:
    due = [
        gate
        for gate in report.gates
        if gate.renewal_required
        or gate.expiry_status
        in {
            EvidenceExpiryStatus.EXPIRED,
            EvidenceExpiryStatus.EXPIRES_SOON,
            EvidenceExpiryStatus.RENEWAL_REQUIRED,
        }
    ]
    section = EvidenceRenewalChecklistSection(
        title="Renewal review",
        items=[
            f"[ ] {gate.evidence_id}: {gate.expiry_status.value}"
            for gate in due
        ]
        or ["[ ] No placeholder renewals currently identified."],
    )
    return "\n".join(
        [
            "# Evidence renewal checklist",
            "",
            "Keep renewal evidence and reviewer activity in the approved private system.",
            "",
            f"## {section.title}",
            "",
            *[f"- {item}" for item in section.items],
            "",
        ]
    )


def render_evidence_signoff_template(
    manifest: EvidenceReviewManifest, report: EvidenceReviewReport
) -> str:
    return (
        "# Evidence signoff template\n\n"
        "This is an unexecuted placeholder template, not a real approval record.\n\n"
        "- Reviewer: `REVIEWER_PLACEHOLDER`\n"
        "- Approver: `APPROVER_PLACEHOLDER`\n"
        "- Review timestamp: `REVIEWED_AT_PLACEHOLDER`\n"
        "- Decision: `DECISION_PLACEHOLDER`\n"
        "- Private signoff ref: `SIGNOFF_REF_PLACEHOLDER`\n\n"
        f"Profile validation blockers: `{report.blocking_findings_count}`\n"
    )


def render_evidence_expiry_report(
    manifest: EvidenceReviewManifest, report: EvidenceReviewReport
) -> str:
    payload = {
        "profile_name": manifest.profile_name,
        "summary": report.summary.model_dump(mode="json"),
        "items": [
            {
                "evidence_id": gate.evidence_id,
                "expiry_status": gate.expiry_status.value,
                "renewal_required": gate.renewal_required,
                "blocks_gate": gate.blocks_gate,
            }
            for gate in report.gates
        ],
        "external_calls": False,
        "notifications_sent": False,
        "values_exposed": False,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_fake_evidence_review_template() -> EvidenceReviewManifest:
    statuses = [
        (
            EvidenceReviewStatus.ACCEPTED_PLACEHOLDER,
            EvidenceExpiryStatus.CURRENT,
            False,
        ),
        (
            EvidenceReviewStatus.NEEDS_REVIEW,
            EvidenceExpiryStatus.NEEDS_REVIEW,
            False,
        ),
        (
            EvidenceReviewStatus.REVIEWED_PLACEHOLDER,
            EvidenceExpiryStatus.EXPIRES_SOON,
            False,
        ),
        (
            EvidenceReviewStatus.REVIEWED_PLACEHOLDER,
            EvidenceExpiryStatus.RENEWAL_REQUIRED,
            True,
        ),
        (
            EvidenceReviewStatus.NOT_APPLICABLE,
            EvidenceExpiryStatus.NOT_APPLICABLE,
            False,
        ),
    ]
    types = [
        EvidenceItemType.DMSA_ONBOARDING,
        EvidenceItemType.SANDBOX_SMOKE,
        EvidenceItemType.SUPPORT_DIAGNOSTICS,
        EvidenceItemType.WEBHOOK_DOCS_VERIFICATION,
        EvidenceItemType.KNOWN_LIMITATIONS,
    ]
    items = []
    for index, (evidence_type, status) in enumerate(zip(types, statuses, strict=True), start=1):
        review_status, expiry_status, renewal_required = status
        items.append(
            EvidenceReviewItem(
                evidence_id=f"EVIDENCE_PLACEHOLDER_{index:03d}",
                evidence_type=evidence_type,
                related_gate=f"B9_GATE_PLACEHOLDER_{evidence_type.value.upper()}",
                evidence_ref_placeholder=(
                    f"PRIVATE_EVIDENCE_REF_PLACEHOLDER_{evidence_type.value.upper()}"
                ),
                review_status=review_status,
                expiry_status=expiry_status,
                renewal_required=renewal_required,
                renewal_reason=(
                    "RENEWAL_REASON_PLACEHOLDER" if renewal_required else ""
                ),
                decision=(
                    EvidenceReviewDecision.RENEWAL_REQUIRED
                    if renewal_required
                    else EvidenceReviewDecision.PENDING
                ),
                notes=["Fake review metadata only; no source material is included."],
                required_for_gate=review_status != EvidenceReviewStatus.NOT_APPLICABLE,
            )
        )
    return EvidenceReviewManifest(
        profile_name="example-evidence-review",
        review_label="Example Evidence Review",
        customer_label="Example Customer",
        environment="staging",
        review_items=items,
        notes=["Fake placeholders only; no real review or signoff is claimed."],
    )


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise EvidenceReviewBlockedError(
            "Evidence review generation blocked: unsafe output root."
        )
    if not output_root.is_absolute() and output_root.parts[0] not in {
        "evidence-review-output",
        "evidence-expiry-output",
        "evidence-renewal-output",
    }:
        raise EvidenceReviewBlockedError(
            "Evidence review generation blocked: use a dedicated output root."
        )
    return output_root.resolve()


def write_evidence_review_artifacts(
    manifest: EvidenceReviewManifest,
    output_root: Path,
    settings: Settings | None = None,
) -> EvidenceReviewArtifactResult:
    settings = settings or get_settings()
    report = build_evidence_review_report(manifest, settings)
    if report.blocking_findings_count and settings.evidence_review_fail_closed:
        raise EvidenceReviewBlockedError(
            "Evidence review generation blocked: manifest failed sanitized validation."
        )
    root = _safe_output_root(Path(output_root))
    if not SAFE_NAME.fullmatch(manifest.profile_name):
        raise EvidenceReviewBlockedError(
            "Evidence review generation blocked: unsafe profile name."
        )
    target = (root / manifest.profile_name).resolve()
    if target.parent != root:
        raise EvidenceReviewBlockedError("Evidence review generation blocked: path traversal.")
    target.mkdir(parents=True, exist_ok=False)
    safe_manifest = sanitize_evidence_review_value(manifest.model_dump(mode="json"))
    names = [
        "review-summary.md",
        "expiry-report.json",
        "renewal-checklist.md",
        "signoff-template.md",
        "review-manifest.template.json",
        "manifest.json",
    ]
    artifact_manifest = {
        "profile_name": manifest.profile_name,
        "files": names,
        "local_only": True,
        "external_calls": False,
        "notifications_sent": False,
        "file_contents_included": False,
    }
    files = {
        "review-summary.md": render_evidence_review_summary(manifest, report),
        "expiry-report.json": render_evidence_expiry_report(manifest, report),
        "renewal-checklist.md": render_evidence_renewal_checklist(manifest, report),
        "signoff-template.md": render_evidence_signoff_template(manifest, report),
        "review-manifest.template.json": (
            json.dumps(safe_manifest, indent=2, sort_keys=True) + "\n"
        ),
        "manifest.json": json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
    }
    for name, content in files.items():
        (target / name).write_text(content, encoding="utf-8")
    return EvidenceReviewArtifactResult(
        profile_name=manifest.profile_name,
        output_directory=manifest.profile_name,
        files=names,
    )

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings, get_settings
from app.schemas.pilot_approval import (
    PilotApprovalArtifactResult,
    PilotApprovalDecision,
    PilotApprovalEvidenceSummary,
    PilotApprovalFinding,
    PilotApprovalGateResult,
    PilotApprovalKnownLimitation,
    PilotApprovalLaunchCondition,
    PilotApprovalPacket,
    PilotApprovalPacketSummary,
    PilotApprovalReadinessSummary,
    PilotApprovalReviewSummary,
    PilotApprovalRiskAcceptance,
    PilotApprovalRollbackCondition,
    PilotApprovalSignoffPlaceholder,
    PilotApprovalStatus,
    PilotApprovalValidationReport,
)

PLACEHOLDER_MARKERS = ("placeholder", "example", "fake", "sample", "demo")
NUMERIC_ID = re.compile(r"(?<![A-Za-z])\d{4,}(?![A-Za-z])")
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
RAW_CONTENT = re.compile(
    r"(?i)(?:raw[_ -]?(?:support bundle|smoke report|webhook report|payload|"
    r"evidence|evidence review)|(?:support bundle|smoke report|webhook report|"
    r"evidence|evidence review)[_ -]?(?:contents?|artifacts?))"
)
BINARY_OR_ARTIFACT = re.compile(
    r"(?i)\.(?:db|sqlite|sqlite3|pdf|docx|xlsx|xls|png|jpe?g|gif|webp|zip|tar|gz|"
    r"support-bundle\.json|smoke\.json|webhook-verification\.json|"
    r"evidence-review\.json|pilot-approval-packet\.(?:json|md)|"
    r"pilot-approval-manifest\.json|pilot-signoff\.md|risk-acceptance\.md|"
    r"launch-conditions\.md|rollback-conditions\.md)$"
)
SAFE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFETY_CODES = {
    "packet_disabled",
    "production_packet",
    "real_id",
    "real_identity",
    "domain",
    "email",
    "phone",
    "secret",
    "signed_url",
    "absolute_path",
    "env_assignment",
    "database_url",
    "storage_url",
    "raw_payload",
    "raw_content",
    "binary_reference",
    "identity_placeholder",
    "max_approvers",
    "max_conditions",
}


class PilotApprovalError(RuntimeError):
    """A sanitized local pilot approval operation failed."""


class PilotApprovalBlockedError(PilotApprovalError):
    """A fail-closed approval packet safety gate blocked execution."""


def sanitize_pilot_approval_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(term in normalized for term in ("authorization", "raw_payload")) or (
                "contents" in normalized and isinstance(item, (str, list, dict))
            ):
                sanitized[str(key)] = "[redacted]"
            else:
                sanitized[str(key)] = sanitize_pilot_approval_value(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_pilot_approval_value(item) for item in value]
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
    code: str, message: str, severity: str = "blocking"
) -> PilotApprovalFinding:
    return PilotApprovalFinding(code=code, severity=severity, message=message)


def _scan_string(value: str) -> set[str]:
    findings = set()
    if NUMERIC_ID.search(value) and not _placeholder(value):
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
    if RAW_CONTENT.search(value):
        findings.add("raw_content")
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
                issues.add("raw_content")
            issues.update(_scan_value(item))
        return issues
    if isinstance(value, (list, tuple)):
        issues = set()
        for item in value:
            issues.update(_scan_value(item))
        return issues
    return _scan_string(value) if isinstance(value, str) else set()


def find_pilot_approval_safety_codes(value: Any) -> set[str]:
    """Return only sanitized safety code names; never return discovered values."""
    return _scan_value(value)


FINDING_MESSAGES = {
    "real_id": "Real-looking numeric identifiers are blocked.",
    "real_identity": "Real-looking reviewer, approver, or operator identities are blocked.",
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
    "raw_content": "Raw evidence, review, support, smoke, or webhook contents are blocked.",
    "binary_reference": "Binary or generated private artifact references are blocked.",
}


def validate_pilot_approval_packet(
    packet: PilotApprovalPacket, settings: Settings
) -> list[PilotApprovalFinding]:
    findings: list[PilotApprovalFinding] = []
    if not settings.pilot_approval_packet_enabled:
        findings.append(_finding("packet_disabled", "Pilot approval packet pattern is disabled."))
    if (
        packet.environment.value == "production"
        and not settings.pilot_approval_packet_allow_production
    ):
        findings.append(_finding("production_packet", "Production approval packets are blocked."))
    approver_count = (
        len(packet.signoff_placeholders)
        + len(packet.reviewed_by_placeholders)
        + len(packet.approved_by_placeholders)
    )
    if approver_count > settings.pilot_approval_packet_max_approvers:
        findings.append(_finding("max_approvers", "Approver count exceeds the safe maximum."))
    if (
        len(packet.launch_conditions) > settings.pilot_approval_packet_max_conditions
        or len(packet.rollback_conditions) > settings.pilot_approval_packet_max_conditions
    ):
        findings.append(_finding("max_conditions", "Condition count exceeds the safe maximum."))
    if settings.pilot_approval_packet_require_placeholders:
        identities = [
            packet.generated_by_placeholder,
            *packet.reviewed_by_placeholders,
            *packet.approved_by_placeholders,
        ]
        for signoff in packet.signoff_placeholders:
            identities.extend(
                [
                    signoff.role_placeholder,
                    signoff.reviewer_placeholder,
                    signoff.approver_placeholder,
                    signoff.signoff_ref_placeholder,
                ]
            )
        if any(value and not _placeholder(value) for value in identities):
            findings.append(
                _finding(
                    "identity_placeholder",
                    "Reviewer, approver, operator, and signoff fields must be placeholders.",
                )
            )
    for code in sorted(_scan_value(packet.model_dump(mode="json"))):
        if code == "real_id" and settings.pilot_approval_packet_allow_real_ids:
            continue
        if code == "real_identity" and settings.pilot_approval_packet_allow_real_identities:
            continue
        if code == "absolute_path" and settings.pilot_approval_packet_allow_absolute_paths:
            continue
        findings.append(_finding(code, FINDING_MESSAGES[code]))
    review = packet.review
    if not packet.launch_conditions:
        findings.append(_finding("launch_conditions", "Launch conditions are required.", "warning"))
    if (
        settings.pilot_approval_packet_require_rollback_conditions
        and not packet.rollback_conditions
    ):
        findings.append(
            _finding("rollback_conditions", "Rollback conditions are required.", "warning")
        )
    if (
        settings.pilot_approval_packet_require_limitations_section
        and not packet.known_limitations
    ):
        findings.append(
            _finding("known_limitations", "Known limitations section is required.", "warning")
        )
    if packet.known_limitations and not packet.risk_acceptance:
        findings.append(
            _finding(
                "risk_acceptance",
                "Known limitations need placeholder risk acceptance.",
                "warning",
            )
        )
    if (
        settings.pilot_approval_packet_require_signoff_placeholders
        and not packet.signoff_placeholders
    ):
        findings.append(
            _finding("signoff_placeholders", "Signoff placeholders are required.", "warning")
        )
    if packet.approval_decision == PilotApprovalDecision.APPROVED_PLACEHOLDER:
        if packet.readiness.pilot_readiness_decision_status.upper() in {"NO_GO", "BLOCKED"}:
            findings.append(
                _finding(
                    "approval_readiness",
                    "Placeholder approval cannot use blocked readiness.",
                    "warning",
                )
            )
        if (
            settings.pilot_approval_packet_require_no_expired_evidence
            and review.expired_evidence_count
        ):
            findings.append(
                _finding(
                    "expired_evidence",
                    "Placeholder approval cannot include expired evidence.",
                    "warning",
                )
            )
        if review.renewal_required_count and (
            not packet.known_limitations or not packet.risk_acceptance
        ):
            findings.append(
                _finding(
                    "renewal_acceptance",
                    "Open renewals require limitations and risk-acceptance placeholders.",
                    "warning",
                )
            )
    if not findings:
        findings.append(
            _finding(
                "safe_packet",
                "Packet contains safe placeholder metadata only.",
                "info",
            )
        )
    return findings


def evaluate_pilot_approval_packet(
    packet: PilotApprovalPacket, settings: Settings
) -> PilotApprovalStatus:
    findings = validate_pilot_approval_packet(packet, settings)
    if any(f.code in SAFETY_CODES and f.severity == "blocking" for f in findings):
        return PilotApprovalStatus.BLOCKED
    if packet.approval_decision == PilotApprovalDecision.REJECTED_PLACEHOLDER:
        return PilotApprovalStatus.REJECTED_PLACEHOLDER
    open_posture = any(f.severity == "warning" for f in findings)
    open_posture = open_posture or any(
        condition.required
        and condition.status
        not in {
            PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            PilotApprovalStatus.APPROVED_PLACEHOLDER,
            PilotApprovalStatus.NOT_APPLICABLE,
        }
        for condition in packet.launch_conditions
    )
    open_posture = open_posture or any(
        condition.status
        not in {
            PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            PilotApprovalStatus.APPROVED_PLACEHOLDER,
            PilotApprovalStatus.NOT_APPLICABLE,
        }
        for condition in packet.rollback_conditions
    )
    open_posture = open_posture or packet.review.expired_evidence_count > 0
    open_posture = open_posture or packet.review.renewal_required_count > 0
    open_posture = open_posture or any(
        limitation.status
        not in {
            PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            PilotApprovalStatus.APPROVED_PLACEHOLDER,
            PilotApprovalStatus.NOT_APPLICABLE,
        }
        for limitation in packet.known_limitations
    )
    open_posture = open_posture or any(
        risk.acceptance_status
        not in {
            PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            PilotApprovalStatus.APPROVED_PLACEHOLDER,
            PilotApprovalStatus.NOT_APPLICABLE,
        }
        for risk in packet.risk_acceptance
    )
    if settings.pilot_approval_packet_require_go_decision:
        open_posture = open_posture or (
            packet.readiness.pilot_readiness_decision_status.upper() != "GO"
        )
    if open_posture:
        return PilotApprovalStatus.NEEDS_REVIEW
    if packet.approval_decision == PilotApprovalDecision.APPROVED_PLACEHOLDER:
        return PilotApprovalStatus.APPROVED_PLACEHOLDER
    return PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW


def build_pilot_approval_validation_report(
    packet: PilotApprovalPacket, settings: Settings
) -> PilotApprovalValidationReport:
    findings = validate_pilot_approval_packet(packet, settings)
    evaluation = evaluate_pilot_approval_packet(packet, settings)
    gates = [
        PilotApprovalGateResult(
            gate="pilot_readiness",
            passed=packet.readiness.pilot_readiness_decision_status.upper()
            not in {"NO_GO", "BLOCKED"},
            status=(
                PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW
                if packet.readiness.pilot_readiness_decision_status.upper()
                not in {"NO_GO", "BLOCKED"}
                else PilotApprovalStatus.BLOCKED
            ),
            summary="Pilot readiness is represented by a placeholder reference and status.",
        ),
        PilotApprovalGateResult(
            gate="evidence_review",
            passed=packet.review.expired_evidence_count == 0
            and packet.review.renewal_required_count == 0,
            status=(
                PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW
                if packet.review.expired_evidence_count == 0
                and packet.review.renewal_required_count == 0
                else PilotApprovalStatus.NEEDS_REVIEW
            ),
            summary="Evidence review posture contains counts and references only.",
        ),
        PilotApprovalGateResult(
            gate="conditions_and_signoff",
            passed=bool(
                packet.launch_conditions
                and packet.rollback_conditions
                and packet.signoff_placeholders
            ),
            status=(
                PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW
                if packet.launch_conditions
                and packet.rollback_conditions
                and packet.signoff_placeholders
                else PilotApprovalStatus.NEEDS_REVIEW
            ),
            summary="Launch, rollback, and signoff placeholders are present.",
        ),
    ]
    return PilotApprovalValidationReport(
        generated_at=datetime.now(UTC),
        packet_name=packet.packet_name,
        environment=packet.environment.value,
        evaluation=evaluation,
        blocking_findings_count=sum(f.severity == "blocking" for f in findings),
        review_findings_count=sum(f.severity == "warning" for f in findings),
        findings=findings,
        gates=gates,
        summary=PilotApprovalPacketSummary(
            launch_conditions=len(packet.launch_conditions),
            rollback_conditions=len(packet.rollback_conditions),
            known_limitations=len(packet.known_limitations),
            risk_acceptances=len(packet.risk_acceptance),
            signoff_placeholders=len(packet.signoff_placeholders),
            expired_evidence_count=packet.review.expired_evidence_count,
            renewal_required_count=packet.review.renewal_required_count,
        ),
    )


def render_pilot_approval_summary(
    packet: PilotApprovalPacket, report: PilotApprovalValidationReport
) -> str:
    return (
        "# Pilot approval summary\n\n"
        "Fake placeholder metadata only. This is not a real pilot approval.\n\n"
        f"- Packet: `{packet.packet_name}`\n"
        f"- Evaluation: `{report.evaluation.value}`\n"
        f"- Safety blockers: `{report.blocking_findings_count}`\n"
        f"- Review findings: `{report.review_findings_count}`\n"
        "- External calls: `false`\n"
        "- Real pilot approved: `false`\n"
    )


def render_launch_conditions(
    packet: PilotApprovalPacket, report: PilotApprovalValidationReport
) -> str:
    lines = ["# Launch conditions", "", "Placeholder conditions only.", ""]
    lines.extend(
        f"- [{condition.status.value}] `{condition.condition_id}`: "
        f"{condition.description_placeholder}"
        for condition in packet.launch_conditions
    )
    return "\n".join(lines) + "\n"


def render_rollback_conditions(
    packet: PilotApprovalPacket, report: PilotApprovalValidationReport
) -> str:
    lines = ["# Rollback conditions", "", "Placeholder triggers and responses only.", ""]
    lines.extend(
        f"- [{condition.status.value}] `{condition.condition_id}`: "
        f"{condition.trigger_placeholder} → {condition.response_placeholder}"
        for condition in packet.rollback_conditions
    )
    return "\n".join(lines) + "\n"


def render_risk_acceptance(
    packet: PilotApprovalPacket, report: PilotApprovalValidationReport
) -> str:
    lines = [
        "# Risk acceptance",
        "",
        "Placeholder planning only; this is not legal, compliance, security, or real approval.",
        "",
    ]
    lines.extend(
        f"- `{risk.limitation_ref}`: {risk.acceptance_status.value} "
        f"({risk.owner_placeholder})"
        for risk in packet.risk_acceptance
    )
    return "\n".join(lines) + "\n"


def render_signoff_template(
    packet: PilotApprovalPacket, report: PilotApprovalValidationReport
) -> str:
    lines = [
        "# Pilot signoff template",
        "",
        "Unexecuted placeholders only; no real signature or approval is recorded.",
        "",
    ]
    for signoff in packet.signoff_placeholders:
        lines.extend(
            [
                f"## {signoff.role_placeholder}",
                "",
                f"- Reviewer: `{signoff.reviewer_placeholder}`",
                f"- Approver: `{signoff.approver_placeholder}`",
                f"- Decision: `{signoff.decision.value}`",
                f"- Reviewed at: `{signoff.reviewed_at_placeholder}`",
                f"- Private ref: `{signoff.signoff_ref_placeholder}`",
                "",
            ]
        )
    return "\n".join(lines)


def render_pilot_approval_packet_markdown(
    packet: PilotApprovalPacket, report: PilotApprovalValidationReport
) -> str:
    lines = [
        "# Pilot approval packet",
        "",
        "Local placeholder packet only; it neither approves nor deploys a pilot.",
        "",
        f"- Pilot: `{packet.pilot_label}`",
        f"- Customer: `{packet.customer_label}`",
        f"- Evaluation: `{report.evaluation.value}`",
        f"- Readiness ref: `{packet.readiness.pilot_readiness_decision_ref}`",
        f"- Evidence ref: `{packet.evidence.evidence_manifest_ref}`",
        f"- Review ref: `{packet.review.evidence_review_ref}`",
        "",
        "## Known limitations",
        "",
    ]
    lines.extend(
        f"- `{item.limitation_id}`: {item.description_placeholder}"
        for item in packet.known_limitations
    )
    return "\n".join(lines) + "\n"


def build_fake_pilot_approval_template() -> PilotApprovalPacket:
    return PilotApprovalPacket(
        packet_name="example-pilot-approval-packet",
        pilot_label="Example Pilot Approval Packet",
        customer_label="Example Customer",
        environment="staging",
        readiness=PilotApprovalReadinessSummary(
            pilot_readiness_decision_ref="PILOT_READINESS_REF_PLACEHOLDER",
            pilot_readiness_decision_status="NEEDS_REVIEW",
        ),
        evidence=PilotApprovalEvidenceSummary(
            evidence_manifest_ref="PRIVATE_EVIDENCE_REF_PLACEHOLDER",
            evidence_item_count_placeholder="EVIDENCE_ITEM_COUNT_PLACEHOLDER",
            evidence_status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
        ),
        review=PilotApprovalReviewSummary(
            evidence_review_ref="EVIDENCE_REVIEW_REF_PLACEHOLDER",
            evidence_review_status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            expired_evidence_count=0,
            renewal_required_count=0,
        ),
        support_diagnostics_ref="SUPPORT_DIAGNOSTICS_REF_PLACEHOLDER",
        support_redaction_status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
        sandbox_smoke_ref="SANDBOX_SMOKE_REF_PLACEHOLDER",
        sandbox_smoke_status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
        webhook_verification_ref="WEBHOOK_VERIFICATION_REF_PLACEHOLDER",
        webhook_verification_status=PilotApprovalStatus.NOT_APPLICABLE,
        migration_safety_ref="MIGRATION_SAFETY_REF_PLACEHOLDER",
        migration_safety_status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
        customer_deployment_profile_ref="CUSTOMER_DEPLOYMENT_REF_PLACEHOLDER",
        customer_deployment_status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
        launch_conditions=[
            PilotApprovalLaunchCondition(
                condition_id="LAUNCH_CONDITION_PLACEHOLDER_001",
                description_placeholder="LAUNCH_REQUIREMENT_PLACEHOLDER",
                status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            )
        ],
        rollback_conditions=[
            PilotApprovalRollbackCondition(
                condition_id="ROLLBACK_CONDITION_PLACEHOLDER_001",
                trigger_placeholder="ROLLBACK_TRIGGER_PLACEHOLDER",
                response_placeholder="ROLLBACK_RESPONSE_PLACEHOLDER",
                status=PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW,
            )
        ],
        known_limitations=[
            PilotApprovalKnownLimitation(
                limitation_id="LIMITATION_PLACEHOLDER_001",
                description_placeholder="KNOWN_LIMITATION_PLACEHOLDER",
                impact_placeholder="LIMITATION_IMPACT_PLACEHOLDER",
                mitigation_placeholder="LIMITATION_MITIGATION_PLACEHOLDER",
                status=PilotApprovalStatus.NEEDS_REVIEW,
            )
        ],
        risk_acceptance=[
            PilotApprovalRiskAcceptance(
                limitation_ref="LIMITATION_PLACEHOLDER_001",
                acceptance_status=PilotApprovalStatus.NEEDS_REVIEW,
            )
        ],
        signoff_placeholders=[
            PilotApprovalSignoffPlaceholder(
                role_placeholder="PRIVATE_REVIEWER_ROLE_PLACEHOLDER"
            )
        ],
        approval_decision=PilotApprovalDecision.DRAFT_PLACEHOLDER,
        approval_status=PilotApprovalStatus.NEEDS_REVIEW,
        approval_notes=["Fake packet only; no real approval is represented."],
        reviewed_by_placeholders=["REVIEWER_PLACEHOLDER"],
        approved_by_placeholders=["APPROVER_PLACEHOLDER"],
    )


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise PilotApprovalBlockedError(
            "Pilot approval generation blocked: unsafe output root."
        )
    if not output_root.is_absolute() and output_root.parts[0] not in {
        "pilot-approval-output",
        "approval-packet-output",
    }:
        raise PilotApprovalBlockedError(
            "Pilot approval generation blocked: use a dedicated output root."
        )
    return output_root.resolve()


def write_pilot_approval_artifacts(
    packet: PilotApprovalPacket,
    output_root: Path,
    settings: Settings | None = None,
) -> PilotApprovalArtifactResult:
    settings = settings or get_settings()
    report = build_pilot_approval_validation_report(packet, settings)
    if (
        report.evaluation == PilotApprovalStatus.BLOCKED
        and settings.pilot_approval_packet_fail_closed
    ):
        raise PilotApprovalBlockedError(
            "Pilot approval generation blocked: packet failed sanitized safety validation."
        )
    root = _safe_output_root(Path(output_root))
    if not SAFE_NAME.fullmatch(packet.packet_name):
        raise PilotApprovalBlockedError(
            "Pilot approval generation blocked: unsafe packet name."
        )
    target = (root / packet.packet_name).resolve()
    if target.parent != root:
        raise PilotApprovalBlockedError("Pilot approval generation blocked: path traversal.")
    target.mkdir(parents=True, exist_ok=False)
    names = [
        "approval-packet.json",
        "approval-packet.md",
        "approval-summary.md",
        "launch-conditions.md",
        "rollback-conditions.md",
        "risk-acceptance.md",
        "signoff-template.md",
        "manifest.json",
    ]
    safe_packet = sanitize_pilot_approval_value(packet.model_dump(mode="json"))
    manifest = {
        "packet_name": packet.packet_name,
        "files": names,
        "local_only": True,
        "external_calls": False,
        "approved_real_pilot": False,
        "file_contents_included": False,
    }
    files = {
        "approval-packet.json": json.dumps(safe_packet, indent=2, sort_keys=True) + "\n",
        "approval-packet.md": render_pilot_approval_packet_markdown(packet, report),
        "approval-summary.md": render_pilot_approval_summary(packet, report),
        "launch-conditions.md": render_launch_conditions(packet, report),
        "rollback-conditions.md": render_rollback_conditions(packet, report),
        "risk-acceptance.md": render_risk_acceptance(packet, report),
        "signoff-template.md": render_signoff_template(packet, report),
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    }
    for name, content in files.items():
        (target / name).write_text(content, encoding="utf-8")
    return PilotApprovalArtifactResult(
        packet_name=packet.packet_name,
        output_directory=packet.packet_name,
        files=names,
    )

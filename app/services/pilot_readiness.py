import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings
from app.schemas.pilot_readiness import (
    PilotReadinessArtifactResult,
    PilotReadinessDecision,
    PilotReadinessEvidenceStatus,
    PilotReadinessFinding,
    PilotReadinessGateResult,
    PilotReadinessGateStatus,
    PilotReadinessProfile,
    PilotReadinessReport,
)
from app.services.diagnostic_redaction import (
    contains_sensitive_material,
    detect_sensitive_patterns,
)

PLACEHOLDER_MARKERS = ("example", "fake", "placeholder", "sample", "demo")
NUMERIC_ID = re.compile(r"^\d{4,}$")
SAFE_REF = re.compile(r"^[A-Z][A-Z0-9_.:/-]{4,200}$")
SENSITIVE_TEXT = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|[\w-]*(?:secret|token|password|signature)\s*[:=])"
)


class PilotReadinessError(RuntimeError):
    """A sanitized pilot readiness planning operation failed."""


class PilotReadinessBlockedError(PilotReadinessError):
    """A fail-closed pilot readiness safety gate blocked execution."""


def sanitize_pilot_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in {"authorization", "raw_payload", "payload", "headers"}:
                result[str(key)] = "[redacted]"
            elif normalized.endswith("_ref"):
                result[str(key)] = item if isinstance(item, str) else "[redacted]"
            elif any(term in normalized for term in ("secret_value", "token_value", "password")):
                result[str(key)] = "[redacted]"
            else:
                result[str(key)] = sanitize_pilot_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_pilot_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if SENSITIVE_TEXT.search(value):
            return "[redacted]"
        if value.startswith(("/Users/", "/home/", "/private/", "/tmp/", "/var/")):
            return "[redacted-path]"
        parsed = urlsplit(value)
        if parsed.scheme and (
            parsed.query or parsed.fragment or parsed.username or parsed.password
        ):
            return "[redacted-url]"
    return value


def _finding(code: str, severity: str, message: str) -> PilotReadinessFinding:
    return PilotReadinessFinding(code=code, severity=severity, message=message)


def _placeholder(value: str) -> bool:
    return any(marker in value.casefold() for marker in PLACEHOLDER_MARKERS)


def _unsafe_value(value: Any) -> set[str]:
    issues = set()
    if isinstance(value, str):
        if SENSITIVE_TEXT.search(value):
            issues.add("sensitive_value")
        if value.startswith(("/Users/", "/home/", "/private/", "/tmp/", "/var/")):
            issues.add("private_path")
        parsed = urlsplit(value)
        if parsed.scheme and re.search(
            r"(?i)(signature|signed|token|expires)=", parsed.query
        ):
            issues.add("signed_url")
        if "support-output/" in value or "customer-output/" in value:
            issues.add("private_output")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in {
                "authorization", "client_secret", "secret_value", "token_value", "password"
            }:
                issues.add("sensitive_value")
            issues.update(_unsafe_value(item))
    elif isinstance(value, list):
        for item in value:
            issues.update(_unsafe_value(item))
    return issues


def _check_ref(
    findings: list[PilotReadinessFinding],
    code: str,
    status: PilotReadinessEvidenceStatus,
    reference: str,
    *,
    required: bool,
) -> None:
    if not required:
        return
    if status != PilotReadinessEvidenceStatus.PASSED:
        findings.append(_finding(
            code, "blocking", "Required evidence status has not passed."
        ))
    if status == PilotReadinessEvidenceStatus.PASSED and not reference:
        findings.append(_finding(
            code, "blocking", "Passed evidence requires a placeholder evidence reference."
        ))
    if reference and not SAFE_REF.fullmatch(reference):
        findings.append(_finding(
            code, "blocking", "Evidence reference must be an uppercase placeholder reference."
        ))


def validate_pilot_readiness_profile(
    profile: PilotReadinessProfile, settings: Settings
) -> list[PilotReadinessFinding]:
    findings: list[PilotReadinessFinding] = []
    if not settings.pilot_readiness_enabled:
        findings.append(_finding(
            "pilot_disabled", "blocking", "Pilot readiness validation is disabled."
        ))
    if (
        profile.environment.value == "production"
        and not settings.pilot_readiness_allow_production
    ):
        findings.append(_finding(
            "production_blocked", "blocking", "Production pilot planning is blocked by default."
        ))
    if settings.pilot_readiness_require_placeholders:
        for label in (profile.pilot_label, profile.customer_label):
            if not _placeholder(label):
                findings.append(_finding(
                    "label_placeholder", "blocking",
                    "Pilot and customer labels must be clearly fake placeholders.",
                ))
        if profile.public_base_url:
            host = (urlsplit(profile.public_base_url).hostname or "").casefold()
            if not host.endswith((".local", ".invalid")):
                findings.append(_finding(
                    "domain_placeholder", "blocking",
                    "Pilot URL must use a fake .local or .invalid host.",
                ))
    if not settings.pilot_readiness_allow_real_ids:
        if NUMERIC_ID.fullmatch(profile.company_id) or any(
            NUMERIC_ID.fullmatch(item) for item in profile.project_ids
        ):
            findings.append(_finding(
                "real_id", "blocking", "Real-looking numeric identifiers are blocked."
            ))
        if not _placeholder(profile.company_id) or any(
            not _placeholder(item) for item in profile.project_ids
        ):
            findings.append(_finding(
                "id_placeholder", "blocking",
                "Company and project identifiers must be obvious placeholders.",
            ))
    for issue in sorted(_unsafe_value(profile.model_dump(mode="json"))):
        findings.append(_finding(
            issue, "blocking", "Pilot profile contains prohibited private or sensitive material."
        ))

    required_checks = [
        (
            "customer_profile", profile.customer_deployment_profile_status,
            profile.customer_profile_ref, True,
        ),
        (
            "dmsa_onboarding", profile.dmsa_onboarding_status,
            profile.dmsa_onboarding_ref, settings.pilot_readiness_require_dmsa_onboarding,
        ),
        (
            "gc_owner_permissions", profile.gc_owner_permission_status,
            profile.gc_owner_permission_ref, settings.pilot_readiness_require_dmsa_onboarding,
        ),
        (
            "private_app_install", profile.private_app_install_status,
            profile.private_app_install_ref, settings.pilot_readiness_require_dmsa_onboarding,
        ),
        (
            "sandbox_smoke", profile.sandbox_smoke_status,
            profile.sandbox_smoke_report_ref,
            settings.pilot_readiness_require_sandbox_smoke
            and not (
                profile.local_only_dry_run
                and profile.environment.value == "local"
                and profile.sandbox_smoke_status
                == PilotReadinessEvidenceStatus.NOT_APPLICABLE
            ),
        ),
        (
            "storage_review", profile.storage_review_status,
            profile.storage_review_ref, settings.pilot_readiness_require_storage_review,
        ),
        (
            "migration_safety", profile.migration_safety_status,
            profile.migration_safety_ref, settings.pilot_readiness_require_migration_safety,
        ),
        (
            "support_diagnostics", profile.support_diagnostics_status,
            profile.support_diagnostics_ref,
            settings.pilot_readiness_require_support_diagnostics,
        ),
        (
            "rollback_plan", profile.rollback_plan_status,
            profile.rollback_plan_ref, settings.pilot_readiness_require_rollback_plan,
        ),
        (
            "backup_plan", profile.backup_plan_status,
            profile.backup_plan_ref, settings.pilot_readiness_require_rollback_plan,
        ),
        (
            "incident_response", profile.incident_response_status,
            profile.incident_response_ref, True,
        ),
        (
            "data_handling", profile.data_handling_review_status,
            profile.data_handling_review_ref, True,
        ),
        (
            "project_scope", profile.allowed_project_scope_status,
            profile.project_scope_ref, True,
        ),
    ]
    for code, status, reference, required in required_checks:
        _check_ref(findings, code, status, reference, required=required)

    pilot_like = profile.environment.value in {"sandbox", "staging", "production"}
    if (
        settings.pilot_readiness_require_admin_auth
        and pilot_like
        and (
            profile.admin_auth_status != PilotReadinessEvidenceStatus.PASSED
            or profile.admin_auth_mode != "token_required"
        )
    ):
        findings.append(_finding(
            "admin_auth", "blocking",
            "Pilot-like environments require passed token-required admin authentication.",
        ))
    if (
        profile.secret_provider_status != PilotReadinessEvidenceStatus.PASSED
        or profile.secret_provider_kind == "external_placeholder"
    ):
        findings.append(_finding(
            "secret_provider", "blocking",
            "Pilot secret provider must be reviewed and implemented, not a placeholder adapter.",
        ))
    if (
        profile.storage_review_status != PilotReadinessEvidenceStatus.PASSED
        or profile.storage_provider_kind == "external_placeholder"
    ):
        findings.append(_finding(
            "storage_provider", "blocking",
            "Pilot storage posture must pass review and use an implemented provider.",
        ))
    if settings.pilot_readiness_require_migration_safety and (
        profile.database_migration_status != PilotReadinessEvidenceStatus.PASSED
        or profile.migration_safety_status != PilotReadinessEvidenceStatus.PASSED
    ):
        findings.append(_finding(
            "migration", "blocking", "Database and migration safety evidence must pass."
        ))
    if (
        pilot_like
        and not profile.local_only_dry_run
        and profile.database_profile.casefold().startswith(("sqlite", "local"))
    ):
        findings.append(_finding(
            "pilot_database", "blocking",
            "A real pilot cannot use a SQLite/local database posture.",
        ))
    if settings.pilot_readiness_require_sandbox_smoke:
        smoke_ok = profile.sandbox_smoke_status == PilotReadinessEvidenceStatus.PASSED
        local_na = (
            profile.local_only_dry_run
            and profile.environment.value == "local"
            and profile.sandbox_smoke_status == PilotReadinessEvidenceStatus.NOT_APPLICABLE
        )
        if not (smoke_ok or local_na):
            findings.append(_finding(
                "sandbox_smoke", "blocking",
                "Required sandbox smoke evidence has not passed.",
            ))
    if settings.pilot_readiness_require_support_diagnostics and (
        profile.support_diagnostics_status != PilotReadinessEvidenceStatus.PASSED
        or profile.support_bundle_redaction_status != PilotReadinessEvidenceStatus.PASSED
    ):
        findings.append(_finding(
            "support_redaction", "blocking",
            "Support diagnostics and redaction evidence must both pass.",
        ))
    if profile.webhooks_planned and settings.pilot_readiness_require_webhook_review:
        if any(status != PilotReadinessEvidenceStatus.PASSED for status in (
            profile.webhook_docs_status,
            profile.webhook_signature_status,
            profile.webhook_verification_status,
        )):
            findings.append(_finding(
                "webhook_review", "blocking",
                "Planned webhooks require passed documentation, signature, "
                "and verification review.",
            ))
        _check_ref(
            findings, "webhook_review", profile.webhook_verification_status,
            profile.webhook_verification_ref, required=True,
        )
    if settings.pilot_readiness_require_operator_approvals:
        for approval in (
            profile.customer_approval_placeholder,
            profile.internal_approval_placeholder,
        ):
            if (
                approval.status != PilotReadinessEvidenceStatus.PASSED
                or not approval.evidence_ref
            ):
                findings.append(_finding(
                    "operator_approval", "blocking",
                    "Required customer and internal approval placeholders must pass with refs.",
                ))
    if profile.monitoring_plan_status == PilotReadinessEvidenceStatus.NEEDS_REVIEW:
        findings.append(_finding(
            "monitoring_plan", "warning", "Monitoring plan still requires review."
        ))
    if profile.known_limitations:
        findings.append(_finding(
            "known_limitations", "warning",
            "Known limitations remain and require explicit controlled-pilot review.",
        ))
    return findings


def _gate(
    category: str,
    statuses: list[PilotReadinessEvidenceStatus],
    reference: str = "",
) -> PilotReadinessGateResult:
    if any(status in {PilotReadinessEvidenceStatus.FAILED, PilotReadinessEvidenceStatus.MISSING}
           for status in statuses):
        status = PilotReadinessGateStatus.FAILED
    elif any(status == PilotReadinessEvidenceStatus.NEEDS_REVIEW for status in statuses):
        status = PilotReadinessGateStatus.NEEDS_REVIEW
    elif all(status in {
        PilotReadinessEvidenceStatus.PASSED,
        PilotReadinessEvidenceStatus.NOT_APPLICABLE,
    } for status in statuses):
        status = PilotReadinessGateStatus.PASSED
    else:
        status = PilotReadinessGateStatus.NEEDS_REVIEW
    return PilotReadinessGateResult(
        category=category,
        status=status,
        summary=f"{category.replace('_', ' ').title()} evidence is {status.value}.",
        evidence_ref_present=bool(reference),
    )


def evaluate_pilot_gate(
    profile: PilotReadinessProfile, settings: Settings
) -> PilotReadinessDecision:
    findings = validate_pilot_readiness_profile(profile, settings)
    safety_codes = {
        "pilot_disabled", "production_blocked", "label_placeholder", "domain_placeholder",
        "real_id", "id_placeholder", "sensitive_value", "private_path", "signed_url",
        "private_output",
    }
    if any(f.code in safety_codes and f.severity == "blocking" for f in findings):
        return PilotReadinessDecision.BLOCKED
    if any(f.severity == "blocking" for f in findings):
        return PilotReadinessDecision.NO_GO
    if any(f.severity == "warning" for f in findings):
        return PilotReadinessDecision.NEEDS_REVIEW
    return PilotReadinessDecision.GO


def build_pilot_readiness_report(
    profile: PilotReadinessProfile, settings: Settings
) -> PilotReadinessReport:
    findings = validate_pilot_readiness_profile(profile, settings)
    gates = [
        _gate("customer_deployment_profile", [profile.customer_deployment_profile_status],
              profile.customer_profile_ref),
        _gate("dmsa_onboarding", [
            profile.dmsa_onboarding_status,
            profile.gc_owner_permission_status,
            profile.private_app_install_status,
        ], profile.dmsa_onboarding_ref),
        _gate("admin_authentication", [profile.admin_auth_status]),
        _gate("secret_provider", [profile.secret_provider_status]),
        _gate("database_migration", [
            profile.database_migration_status, profile.migration_safety_status,
        ], profile.migration_safety_ref),
        _gate("attachment_storage", [profile.storage_review_status], profile.storage_review_ref),
        _gate("webhook_review", [
            profile.webhook_docs_status,
            profile.webhook_signature_status,
            profile.webhook_verification_status,
        ], profile.webhook_verification_ref),
        _gate("sandbox_smoke", [profile.sandbox_smoke_status], profile.sandbox_smoke_report_ref),
        _gate("support_diagnostics", [
            profile.support_diagnostics_status, profile.support_bundle_redaction_status,
        ], profile.support_diagnostics_ref),
        _gate("rollback_backup", [
            profile.rollback_plan_status, profile.backup_plan_status,
        ], profile.rollback_plan_ref),
        _gate("incident_response", [profile.incident_response_status],
              profile.incident_response_ref),
        _gate("data_handling", [profile.data_handling_review_status],
              profile.data_handling_review_ref),
        _gate("project_allowlist", [profile.allowed_project_scope_status],
              profile.project_scope_ref),
        _gate("operator_approvals", [
            profile.customer_approval_placeholder.status,
            profile.internal_approval_placeholder.status,
        ]),
        _gate("known_limitations", [profile.monitoring_plan_status]),
    ]
    decision = evaluate_pilot_gate(profile, settings)
    return PilotReadinessReport(
        generated_at=datetime.now(UTC),
        profile_name=_safe_name(profile.profile_name),
        environment=profile.environment.value,
        decision=decision,
        gates=gates,
        findings=findings,
        blocking_count=sum(f.severity == "blocking" for f in findings),
        review_count=sum(f.severity == "warning" for f in findings),
    )


def render_go_no_go_summary(
    profile: PilotReadinessProfile, report: PilotReadinessReport
) -> str:
    return f"""# Pilot go/no-go summary

- Profile: `{_safe_name(profile.profile_name)}`
- Environment: `{profile.environment.value}`
- Decision: **{report.decision.value}**
- Blocking findings: {report.blocking_count}
- Review findings: {report.review_count}
- Deployed: false
- External calls: false

This local gate is not production deployment approval, security certification, customer approval,
or authorization to call Procore.
"""


def render_pilot_launch_checklist(
    profile: PilotReadinessProfile, report: PilotReadinessReport
) -> str:
    items = "\n".join(
        f"- [{'x' if gate.status == PilotReadinessGateStatus.PASSED else ' '}] "
        f"{gate.category.replace('_', ' ').title()}: {gate.status.value}"
        for gate in report.gates
    )
    return f"""# Controlled pilot launch checklist

Decision: **{report.decision.value}**

{items}

Do not launch while the decision is NO_GO, NEEDS_REVIEW, or BLOCKED. A GO means only that this
local placeholder profile passed configured gates; separate private approvals still control any
real pilot.
"""


def render_pilot_operator_signoff(
    profile: PilotReadinessProfile, report: PilotReadinessReport
) -> str:
    del profile
    return f"""# Pilot operator signoff template

Gate decision: **{report.decision.value}**

- Customer approver: `APPROVER_PLACEHOLDER`
- Internal approver: `APPROVER_PLACEHOLDER`
- Pilot owner: `PILOT_OWNER_PLACEHOLDER`
- Technical owner: `TECHNICAL_OWNER_PLACEHOLDER`
- Launch window: `LAUNCH_WINDOW_PLACEHOLDER`

No signature or real approval is recorded in this generated public-safe template.
"""


def render_pilot_readiness_markdown(
    profile: PilotReadinessProfile, report: PilotReadinessReport
) -> str:
    findings = "\n".join(
        f"- [{finding.severity}] {finding.code}: {finding.message}"
        for finding in report.findings
    )
    return (
        render_go_no_go_summary(profile, report)
        + "\n## Findings\n\n"
        + (findings or "- No configured findings.")
        + "\n"
    )


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-z0-9-]+", "-", value.casefold()).strip("-")
    if not safe or safe in {".", ".."}:
        raise PilotReadinessBlockedError("Pilot profile name is unsafe.")
    return safe[:80]


def _safe_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise PilotReadinessBlockedError("Pilot readiness output path is unsafe.")
    return output_root.resolve()


def write_pilot_readiness_artifacts(
    profile: PilotReadinessProfile,
    output_root: Path,
    settings: Settings | None = None,
) -> PilotReadinessArtifactResult:
    configured = settings or Settings(_env_file=None)
    report = build_pilot_readiness_report(profile, configured)
    if configured.pilot_readiness_fail_closed and report.decision in {
        PilotReadinessDecision.NO_GO,
        PilotReadinessDecision.BLOCKED,
    }:
        raise PilotReadinessBlockedError(
            "Pilot artifact generation blocked by the go/no-go decision."
        )
    root = _safe_root(output_root)
    directory = root / _safe_name(profile.profile_name)
    if not directory.is_relative_to(root):
        raise PilotReadinessBlockedError("Pilot readiness output escaped its root.")
    directory.mkdir(parents=True, exist_ok=True)
    contents = {
        "pilot-readiness-report.json": report.model_dump_json(indent=2) + "\n",
        "go-no-go.md": render_go_no_go_summary(profile, report),
        "launch-checklist.md": render_pilot_launch_checklist(profile, report),
        "operator-signoff.md": render_pilot_operator_signoff(profile, report),
        "known-limitations.md": (
            "# Known limitations\n\n"
            + "\n".join(f"- {item}" for item in profile.known_limitations)
            + "\n"
        ),
    }
    for name, content in contents.items():
        if detect_sensitive_patterns(content) or contains_sensitive_material(content):
            raise PilotReadinessBlockedError(
                "Generated pilot artifact failed strict redaction validation."
            )
        (directory / name).write_text(content)
    manifest_items = []
    for name in sorted(contents):
        data = (directory / name).read_bytes()
        manifest_items.append({
            "name": name,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    (directory / "manifest.json").write_text(
        json.dumps({"files": manifest_items}, indent=2, sort_keys=True) + "\n"
    )
    return PilotReadinessArtifactResult(
        profile_name=_safe_name(profile.profile_name),
        output_directory=directory.relative_to(root).as_posix(),
        files=sorted([*contents, "manifest.json"]),
    )

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.hosted_pilot_dry_run import (
    HostedPilotDryRunArtifactResult,
    HostedPilotDryRunDecision,
    HostedPilotDryRunEvidenceRef,
    HostedPilotDryRunFinding,
    HostedPilotDryRunProfile,
    HostedPilotDryRunReport,
    HostedPilotDryRunRequirement,
    HostedPilotDryRunStatus,
)

SAFE_PLACEHOLDER = re.compile(r"^[A-Z0-9_-]*PLACEHOLDER[A-Z0-9_-]*$")
SAFE_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
RAW_URL = re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mysql|mongodb)://\S+")
DOMAIN = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud)\b")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\b(?:\+?1[-. ]?)?\d{3}[-. ]\d{3}[-. ]\d{4}\b")
LONG_ID = re.compile(r"\b(?:\d{9,}|[a-f0-9]{24,}|[A-Za-z0-9_-]{40,})\b")
CLOUD_ID = re.compile(
    r"(?i)(?:\barn:aws[a-z-]*:\S+|\b\d{12}\b|/subscriptions/[0-9a-f-]{20,}|"
    r"\bprojects/[a-z0-9-]{6,}\b|"
    r"\b(?:account|subscription|tenant|project|resource|service|cluster|app)"
    r"[_ -]?id\s*[:=]\s*[a-z0-9-]{6,})"
)
REGISTRY_REF = re.compile(
    r"(?i)\b(?:[a-z0-9.-]+\.)?[a-z0-9.-]+/[a-z0-9._/-]+:"
    r"(?:latest|v?\d[\w.-]*|[a-f0-9]{7,})\b"
)
CERTIFICATE = re.compile(
    r"(?i)(?:-----BEGIN (?:RSA |EC |OPENSSH )?(?:CERTIFICATE|PRIVATE KEY)|"
    r"-----BEGIN CERTIFICATE REQUEST-----|\b(?:private_key|certificate|csr|"
    r"acme[-_ ]challenge)\s*[:=]\s*\S+|_acme-challenge\.)"
)
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+|(?:secret|token|password|credential|"
    r"app[_ -]?version[_ -]?key)\s*[:=]\s*\S+)"
)
SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires)=")
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
REPORT_CONTENT = re.compile(
    r"(?i)(?:raw[_ -]?(?:report|payload|response|evidence)|"
    r"(?:report|evidence|support bundle|smoke report|webhook report)[_ -]?contents?|"
    r"(?:subject|description|response_body|headers)\s*[:=])"
)
LIVE_RESULT = re.compile(
    r'(?i)^\s*\{.*"(?:status_code|response_body|records|results|deployment_id)"\s*:'
)
DEPLOYMENT_LOG = re.compile(
    r"(?i)(?:deployment (?:log|output|result)|build log|release log|"
    r"migration log|restore log|backup log|\.sql\b|\.dump\b|\.backup\b|\.pgdump\b)"
)
APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:approved for (?:launch|pilot|production)|pilot (?:is )?approved|"
    r"launch (?:is )?approved|production[- ]ready|ready for production|"
    r"security (?:is )?complete|dry run (?:proves|equals) launch approval)\b"
)

REF_FIELDS = (
    "secret_provider_plan_ref",
    "storage_provider_plan_ref",
    "postgres_runtime_plan_ref",
    "hosted_deployment_plan_ref",
    "https_webhook_plan_ref",
    "sandbox_smoke_evidence_ref",
    "sandbox_read_validation_evidence_ref",
    "sandbox_evidence_linkage_ref",
    "pilot_readiness_ref",
    "pilot_approval_packet_ref",
    "rollback_plan_ref",
    "disable_plan_ref",
    "diagnostics_plan_ref",
    "support_bundle_plan_ref",
    "monitoring_plan_ref",
    "incident_response_ref",
    "data_handling_ref",
)
ARTIFACT_FILES = [
    "hosted-pilot-dry-run-report.json",
    "pilot-dry-run-checklist.md",
    "pilot-dry-run-runbook.md",
    "pilot-dry-run-evidence-map.md",
    "pilot-dry-run-blockers.md",
    "manifest.json",
]
SAFE_OUTPUT_ROOTS = {
    "hosted-pilot-dry-run-output",
    "pilot-dry-run-output",
    "operations-dry-run-output",
    "launch-rehearsal-output",
}


class HostedPilotDryRunError(RuntimeError):
    """Hosted pilot dry-run planning failed with private details suppressed."""


class HostedPilotDryRunBlockedError(HostedPilotDryRunError):
    pass


def _strings(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def sanitize_hosted_pilot_dry_run_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_hosted_pilot_dry_run_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_hosted_pilot_dry_run_value(item) for item in value]
    if isinstance(value, Path):
        return "[masked-path]"
    if isinstance(value, str) and not SAFE_PLACEHOLDER.fullmatch(value):
        for pattern, replacement in (
            (SIGNED_URL, "[masked-url]"),
            (RAW_URL, "[masked-url]"),
            (DOMAIN, "[masked-domain]"),
            (EMAIL, "[masked-identity]"),
            (PHONE, "[masked-identity]"),
            (CLOUD_ID, "[masked-infrastructure-identifier]"),
            (REGISTRY_REF, "[masked-registry-reference]"),
            (CERTIFICATE, "[masked-certificate-material]"),
            (SECRET, "[masked-secret]"),
            (ABSOLUTE_PATH, "[masked-path]"),
            (REPORT_CONTENT, "[masked-report-content]"),
            (LIVE_RESULT, "[masked-live-result]"),
            (DEPLOYMENT_LOG, "[masked-operation-output]"),
            (APPROVAL_CLAIM, "[masked-claim]"),
            (LONG_ID, "[masked-identifier]"),
        ):
            if pattern.search(value):
                return replacement
    return value


def _finding(code: str) -> HostedPilotDryRunFinding:
    return HostedPilotDryRunFinding(
        code=code,
        message=f"Unsafe {code.replace('_', ' ')} is blocked.",
    )


def validate_hosted_pilot_dry_run_ref(
    ref: str, settings: Settings
) -> list[HostedPilotDryRunFinding]:
    findings: list[HostedPilotDryRunFinding] = []
    if not ref:
        return findings
    checks = (
        ("signed_url", SIGNED_URL),
        ("raw_url", RAW_URL),
        ("real_domain", DOMAIN),
        ("email", EMAIL),
        ("phone", PHONE),
        ("cloud_id", CLOUD_ID),
        ("registry_ref", REGISTRY_REF),
        ("certificate_material", CERTIFICATE),
        ("secret", SECRET),
        ("absolute_path", ABSOLUTE_PATH),
        ("raw_report_content", REPORT_CONTENT),
        ("live_result_payload", LIVE_RESULT),
        ("deployment_log", DEPLOYMENT_LOG),
        ("approval_claim", APPROVAL_CLAIM),
        ("long_id", LONG_ID),
    )
    if SAFE_PLACEHOLDER.fullmatch(ref):
        return findings
    for code, pattern in checks:
        if pattern.search(ref):
            findings.append(_finding(code))
    if settings.hosted_pilot_dry_run_require_placeholders:
        findings.append(_finding("placeholder_required"))
    return findings


def validate_hosted_pilot_dry_run_profile(
    profile: HostedPilotDryRunProfile, settings: Settings
) -> list[HostedPilotDryRunFinding]:
    findings: list[HostedPilotDryRunFinding] = []
    if not settings.hosted_pilot_dry_run_enabled:
        findings.append(_finding("dry_run_disabled"))
    if not settings.hosted_pilot_dry_run_fail_closed:
        findings.append(_finding("fail_closed_disabled"))
    if not SAFE_PROFILE_NAME.fullmatch(profile.profile_name):
        findings.append(_finding("profile_name"))
    if any(
        (
            settings.hosted_pilot_dry_run_allow_real_identities,
            settings.hosted_pilot_dry_run_allow_real_domains,
            settings.hosted_pilot_dry_run_allow_real_urls,
            settings.hosted_pilot_dry_run_allow_real_infra_ids,
            settings.hosted_pilot_dry_run_allow_report_contents,
            settings.hosted_pilot_dry_run_allow_absolute_paths,
        )
    ):
        findings.append(_finding("unsafe_policy"))
    values = [getattr(profile, name) for name in REF_FIELDS]
    values.extend(
        (
            profile.environment_label,
            profile.reviewer_placeholder,
            profile.expiry_placeholder,
        )
    )
    values.extend(profile.known_limitations)
    values.extend(profile.notes)
    refs_total = sum(bool(value) for value in values)
    if refs_total > settings.hosted_pilot_dry_run_max_refs:
        findings.append(_finding("too_many_refs"))
    for value in values:
        findings.extend(validate_hosted_pilot_dry_run_ref(value, settings))
    return list({(item.code, item.message): item for item in findings}.values())


def build_default_hosted_pilot_dry_run_profile(
    settings: Settings,
) -> HostedPilotDryRunProfile:
    del settings
    return HostedPilotDryRunProfile(profile_name="example-hosted-pilot-dry-run")


def build_hosted_pilot_dry_run_report(
    profile: HostedPilotDryRunProfile, settings: Settings
) -> HostedPilotDryRunReport:
    findings = validate_hosted_pilot_dry_run_profile(profile, settings)
    refs = [(name, getattr(profile, name)) for name in REF_FIELDS]
    missing = [name for name, value in refs if not value]
    requirements = [
        HostedPilotDryRunRequirement(
            name=name,
            present=bool(value),
            status=(
                HostedPilotDryRunStatus.ACCEPTED_PLACEHOLDER
                if value
                else HostedPilotDryRunStatus.MISSING
            ),
            message="Opaque placeholder reference accepted." if value else "Reference is missing.",
        )
        for name, value in refs
    ]
    evidence_refs = [
        HostedPilotDryRunEvidenceRef(
            name=name,
            value=value,
            status=(
                HostedPilotDryRunStatus.ACCEPTED_PLACEHOLDER
                if value
                else HostedPilotDryRunStatus.MISSING
            ),
        )
        for name, value in refs
    ]
    if findings:
        status = HostedPilotDryRunStatus.BLOCKED
        decision = HostedPilotDryRunDecision.BLOCKED
    elif missing:
        status = HostedPilotDryRunStatus.NEEDS_REVIEW
        decision = HostedPilotDryRunDecision.NEEDS_REVIEW
    else:
        status = HostedPilotDryRunStatus.READY_FOR_PRIVATE_REHEARSAL
        decision = HostedPilotDryRunDecision.READY_FOR_PRIVATE_REVIEW
    return HostedPilotDryRunReport(
        profile_name=profile.profile_name,
        status=status,
        decision=decision,
        refs_total=sum(bool(value) for _, value in refs),
        required_refs_present=len(refs) - len(missing),
        missing_refs=missing,
        blocker_summary=[item.code for item in findings],
        requirements=requirements,
        evidence_refs=evidence_refs,
        findings=findings,
        recommended_next_steps=[
            "Review the opaque references in a private workspace.",
            "Resolve missing references and blockers manually.",
            "Require human review before any separately authorized launch activity.",
            "Keep private materials, credentials, and operations outside this pack.",
        ],
    )


def _header(title: str, profile: HostedPilotDryRunProfile) -> list[str]:
    return [
        f"# {title}",
        "",
        f"Profile: `{profile.profile_name}`",
        "",
        "Public-safe rehearsal only. This dry run is not a launch or pilot approval.",
        "No live operation occurred and no private report contents were read.",
        "",
    ]


def render_hosted_pilot_dry_run_checklist(profile, report) -> str:
    lines = _header("Hosted pilot dry-run checklist", profile)
    lines.extend(
        f"- [{'x' if item.present else ' '}] {item.name}: {item.status}"
        for item in report.requirements
    )
    lines.extend(["", "- [ ] Complete human review privately before any launch decision."])
    return "\n".join(lines) + "\n"


def render_hosted_pilot_dry_run_runbook(profile, report) -> str:
    del report
    lines = _header("Hosted pilot operations rehearsal runbook", profile)
    lines.extend(
        [
            "1. Validate placeholder references offline.",
            "2. Map G1–G5 plans without opening linked evidence.",
            "3. Review rollback, disable, monitoring, diagnostics, and incident references.",
            "4. Record blockers privately and keep launch on hold.",
            "5. Obtain separate human approval through the private process.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_hosted_pilot_dry_run_evidence_map(profile, report) -> str:
    lines = _header("Hosted pilot dry-run evidence map", profile)
    lines.extend(f"- {item.name}: `{item.value or 'MISSING'}`" for item in report.evidence_refs)
    lines.extend(["", "References are opaque labels only; linked contents were not read."])
    return "\n".join(lines) + "\n"


def render_hosted_pilot_dry_run_blockers(profile, report) -> str:
    lines = _header("Hosted pilot dry-run blockers", profile)
    if report.blocker_summary:
        lines.extend(f"- {item}" for item in report.blocker_summary)
    elif report.missing_refs:
        lines.extend(f"- Missing reference: {item}" for item in report.missing_refs)
    else:
        lines.append(
            "- No public-safe profile blocker detected; private human review remains required."
        )
    return "\n".join(lines) + "\n"


def validate_hosted_pilot_dry_run_report_safe(
    report: HostedPilotDryRunReport,
) -> None:
    for value in _strings(report.model_dump(mode="json")):
        if SAFE_PLACEHOLDER.fullmatch(value):
            continue
        for pattern in (
            RAW_URL,
            DOMAIN,
            EMAIL,
            PHONE,
            CLOUD_ID,
            REGISTRY_REF,
            CERTIFICATE,
            SECRET,
            ABSOLUTE_PATH,
            REPORT_CONTENT,
            LIVE_RESULT,
            DEPLOYMENT_LOG,
            APPROVAL_CLAIM,
            LONG_ID,
        ):
            if pattern.search(value):
                raise HostedPilotDryRunBlockedError(
                    "Dry-run report failed safety validation."
                )
    operation_flags = (
        report.dry_run_execution_attempted,
        report.live_operation_attempted,
        report.deployment_attempted,
        report.procore_call_attempted,
        report.db_connection_attempted,
        report.cloud_call_attempted,
        report.webhook_registration_attempted,
        report.report_contents_exposed,
        report.secrets_exposed,
        report.ids_exposed,
        report.real_urls_exposed,
        report.real_domains_exposed,
        report.private_paths_exposed,
    )
    if any(operation_flags):
        raise HostedPilotDryRunBlockedError("Dry-run report contains unsafe operation flags.")


def write_hosted_pilot_dry_run_artifacts(
    profile: HostedPilotDryRunProfile, output_root: Path
) -> HostedPilotDryRunArtifactResult:
    temporary_absolute = (
        output_root.is_absolute()
        and output_root.name.startswith("procore-intake-bridge-hosted-pilot-dry-run-")
        and (output_root.parent == Path("/tmp") or "pytest-" in output_root.as_posix())
    )
    if ".." in output_root.parts or (output_root.is_absolute() and not temporary_absolute):
        raise HostedPilotDryRunBlockedError("Dry-run output root is unsafe.")
    if not temporary_absolute and output_root.parts[:1] not in {
        (name,) for name in SAFE_OUTPUT_ROOTS
    }:
        raise HostedPilotDryRunBlockedError("Dry-run output root is not approved.")
    report = build_hosted_pilot_dry_run_report(profile, Settings(_env_file=None))
    if report.status == HostedPilotDryRunStatus.BLOCKED:
        raise HostedPilotDryRunBlockedError("Dry-run profile failed safety validation.")
    validate_hosted_pilot_dry_run_report_safe(report)
    destination = output_root / profile.profile_name
    destination.mkdir(parents=True, exist_ok=True)
    rendered = {
        "hosted-pilot-dry-run-report.json": json.dumps(
            report.model_dump(mode="json"), indent=2, sort_keys=True
        )
        + "\n",
        "pilot-dry-run-checklist.md": render_hosted_pilot_dry_run_checklist(profile, report),
        "pilot-dry-run-runbook.md": render_hosted_pilot_dry_run_runbook(profile, report),
        "pilot-dry-run-evidence-map.md": render_hosted_pilot_dry_run_evidence_map(profile, report),
        "pilot-dry-run-blockers.md": render_hosted_pilot_dry_run_blockers(profile, report),
        "manifest.json": json.dumps(
            {
                "files": ARTIFACT_FILES,
                "placeholder_only": True,
                "report_contents_read": False,
                "live_operations": False,
                "deployment_attempted": False,
                "approval_claimed": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    }
    for name, content in rendered.items():
        (destination / name).write_text(content, encoding="utf-8")
    return HostedPilotDryRunArtifactResult(
        profile_name=profile.profile_name,
        output_directory=profile.profile_name,
        files=ARTIFACT_FILES,
    )

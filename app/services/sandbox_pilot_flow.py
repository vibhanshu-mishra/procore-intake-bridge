import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.sandbox_pilot_flow import (
    FlowArtifactResult,
    FlowDecision,
    FlowFinding,
    FlowMilestone,
    FlowMode,
    FlowProfile,
    FlowReadinessReport,
    FlowRequirement,
    FlowStage,
    FlowStatus,
)

PLACEHOLDER = re.compile(r"(?i)(placeholder|example|fake|sample|not_configured)")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{2,63}$")
PATTERNS = (
    ("raw_url", re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mysql|s3|gs)://\S+")),
    ("domain", re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud)\b")),
    (
        "secret",
        re.compile(
            r"(?i)(authorization\s*:|bearer\s+|(?:secret|token|password|credential)\s*[:=]\s*\S+)"
        ),
    ),
    ("signed_url", re.compile(r"(?i)[?&](?:signature|signed|token|expires)=")),
    ("certificate", re.compile(r"(?i)(-----BEGIN|private[_ -]?key|certificate[_ -]?contents?)")),
    ("cloud_credentials", re.compile(r'(?i)"(?:private_key|client_email|access_key_id)"\s*:')),
    (
        "infrastructure_id",
        re.compile(r"(?i)\b(?:vpc|subnet|arn|subscription|account|cluster)[-_:/.][a-z0-9-]{4,}\b"),
    ),
    ("absolute_path", re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")),
    ("env_assignment", re.compile(r"(?m)^[A-Z][A-Z0-9_]{2,}\s*=\s*(?![A-Z0-9_]*PLACEHOLDER)\S+")),
    ("blocked_file", re.compile(r"(?i)\.(?:sql|dump|backup|bak|pgdump|log|pem|key|crt|csr)\b")),
    (
        "raw_content",
        re.compile(
            r"(?i)(?:raw|contents?)\s+(?:support bundle|smoke report|"
            r"webhook (?:report|payload)|evidence|deployment log)"
        ),
    ),
    ("email", re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-. ]?)?\d{3}[-. ]\d{3}[-. ]\d{4}\b")),
    ("procore_id", re.compile(r"(?<!\w)\d{6,}(?!\w)")),
)
ARTIFACTS = (
    "flow-report.json",
    "flow-summary.md",
    "sandbox-to-pilot-plan.md",
    "sandbox-onboarding-checklist.md",
    "pilot-preflight-checklist.md",
    "launch-hold.md",
    "manifest.json",
)


class SandboxPilotFlowError(RuntimeError):
    """Flow operation failed with private details suppressed."""


class SandboxPilotFlowBlockedError(SandboxPilotFlowError):
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


def sanitize_flow_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): sanitize_flow_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_flow_value(v) for v in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        for code, pattern in PATTERNS:
            if pattern.search(value):
                return f"[masked-{code.replace('_', '-')}]"
    return value


def validate_flow_profile(profile: FlowProfile, settings: Settings) -> list[FlowFinding]:
    findings: list[FlowFinding] = []
    if not settings.sandbox_pilot_flow_enabled:
        findings.append(
            FlowFinding(
                code="flow_disabled",
                severity="blocking",
                message="Sandbox-to-pilot flow is disabled.",
            )
        )
    if not SAFE_NAME.fullmatch(profile.profile_name):
        findings.append(
            FlowFinding(
                code="profile_name",
                severity="blocking",
                message="Profile name must be a safe display name.",
            )
        )
    if (
        profile.selected_path == FlowMode.PILOT
        and not settings.sandbox_pilot_flow_allow_production
        and "production" in profile.environment_label.casefold()
    ):
        findings.append(
            FlowFinding(
                code="production",
                severity="blocking",
                message="Production flow is blocked by default.",
            )
        )
    for value in _strings(profile.model_dump(mode="json")):
        for code, pattern in PATTERNS:
            if pattern.search(value) and not (
                code in {"domain", "procore_id"} and PLACEHOLDER.search(value)
            ):
                findings.append(
                    FlowFinding(
                        code=code,
                        severity="blocking",
                        message=f"Unsafe {code.replace('_', ' ')} material is not allowed.",
                    )
                )
        if re.fullmatch(r"[A-Z][A-Z0-9_]*_PLACEHOLDER", value):
            continue
        if re.search(r"(?i)\b(?:reviewer|approver|operator)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b", value):
            findings.append(
                FlowFinding(
                    code="identity",
                    severity="blocking",
                    message="Real-looking identities are not allowed.",
                )
            )
    if profile.selected_path == FlowMode.SANDBOX:
        required = (
            ("dmsa_refs", profile.dmsa_refs_status, settings.flow_require_dmsa_refs_for_sandbox),
            (
                "project_scope",
                profile.allowed_scope_status,
                settings.flow_require_project_scope_for_sandbox,
            ),
            ("admin_auth", profile.admin_auth_status, settings.flow_require_admin_auth_for_sandbox),
        )
        for code, status, enabled in required:
            if enabled and status == FlowStatus.NOT_APPLICABLE:
                findings.append(
                    FlowFinding(
                        code=code,
                        severity="blocking",
                        message=f"Required sandbox {code.replace('_', ' ')} cannot be omitted.",
                    )
                )
    if profile.selected_path == FlowMode.PILOT:
        placeholders = (
            ("sandbox_smoke_ref", profile.sandbox_smoke_ref),
            ("legal_privacy_review", profile.legal_privacy_review_placeholder),
            ("customer_approval", profile.customer_approval_placeholder),
            ("operator_approval", profile.internal_operator_approval_placeholder),
        )
        for code, value in placeholders:
            if not PLACEHOLDER.search(value):
                findings.append(
                    FlowFinding(
                        code=code,
                        severity="blocking",
                        message=f"Pilot {code.replace('_', ' ')} placeholder is required.",
                    )
                )
        for code, status in (
            ("rollback", profile.rollback_status),
            ("backup", profile.backup_status),
        ):
            if status == FlowStatus.NOT_APPLICABLE:
                findings.append(
                    FlowFinding(
                        code=code,
                        severity="blocking",
                        message=f"Pilot {code} planning cannot be omitted.",
                    )
                )
    return list({(f.code, f.message): f for f in findings}.values())


def _require(
    profile: FlowProfile, name: str, stage: FlowStage, attr: str, message: str
) -> FlowRequirement:
    status = getattr(profile, attr)
    return FlowRequirement(requirement=name, stage=stage, status=status, message=message)


def evaluate_demo_path(profile: FlowProfile, settings: Settings) -> list[FlowRequirement]:
    return [
        _require(
            profile,
            "fixture_demo",
            FlowStage.DEMO,
            "demo_status",
            "Run fixture-only demo and local checks.",
        )
    ]


def evaluate_sandbox_path(profile: FlowProfile, settings: Settings) -> list[FlowRequirement]:
    items = [
        ("demo_ready", "demo_status", "Complete the fixture demo first."),
        ("dmsa_secret_refs", "dmsa_refs_status", "Record private DMSA secret references."),
        (
            "allowed_project_scope",
            "allowed_scope_status",
            "Record allowed company/project scope privately.",
        ),
        ("admin_auth", "admin_auth_status", "Configure secret-backed admin authentication."),
        ("permission_review", "permission_review_status", "Review read-only DMSA permissions."),
        (
            "sandbox_smoke_evidence",
            "sandbox_smoke_status",
            "Run the separately gated smoke test later and record only its private reference.",
        ),
        (
            "webhook_review",
            "webhook_review_status",
            "Review webhook posture without registering anything.",
        ),
    ]
    return [_require(profile, n, FlowStage.SANDBOX_ONBOARDING, a, m) for n, a, m in items]


def evaluate_pilot_path(profile: FlowProfile, settings: Settings) -> list[FlowRequirement]:
    attrs = [
        ("sandbox_smoke_evidence", "sandbox_smoke_status"),
        ("private_workspace", "private_workspace_status"),
        ("secret_provider", "secret_provider_status"),
        ("storage_provider", "storage_provider_status"),
        ("postgres_database", "database_status"),
        ("deployment_recipe", "deployment_recipe_status"),
        ("support_diagnostics", "support_diagnostics_status"),
        ("evidence_manifest", "evidence_manifest_status"),
        ("evidence_review", "evidence_review_status"),
        ("pilot_readiness", "pilot_readiness_status"),
        ("approval_packet_private_review", "pilot_approval_status"),
        ("rollback_plan", "rollback_status"),
        ("backup_plan", "backup_status"),
        ("incident_response", "incident_response_status"),
    ]
    return [
        _require(
            profile,
            n,
            FlowStage.PILOT_PREFLIGHT,
            a,
            f"Complete private {n.replace('_', ' ')} readiness.",
        )
        for n, a in attrs
    ]


def build_sandbox_pilot_flow_report(
    profile: FlowProfile, settings: Settings
) -> FlowReadinessReport:
    findings = validate_flow_profile(profile, settings)
    if profile.selected_path == FlowMode.DEMO:
        requirements = evaluate_demo_path(profile, settings)
        ready_decision, needs_decision = FlowDecision.DEMO_READY, FlowDecision.BLOCKED
    elif profile.selected_path == FlowMode.SANDBOX:
        requirements = evaluate_sandbox_path(profile, settings)
        ready_decision, needs_decision = (
            FlowDecision.SANDBOX_READY,
            FlowDecision.SANDBOX_NEEDS_CONFIGURATION,
        )
    else:
        requirements = evaluate_pilot_path(profile, settings)
        ready_decision, needs_decision = (
            FlowDecision.PILOT_READY_FOR_PRIVATE_REVIEW,
            FlowDecision.PILOT_NEEDS_CONFIGURATION,
        )
    blocked = bool(findings)
    ready = all(item.status == FlowStatus.READY for item in requirements)
    decision = FlowDecision.BLOCKED if blocked else ready_decision if ready else needs_decision
    status = (
        FlowStatus.BLOCKED
        if blocked
        else FlowStatus.READY
        if ready
        else FlowStatus.NEEDS_CONFIGURATION
    )
    next_steps = [item.message for item in requirements if item.status != FlowStatus.READY]
    if profile.selected_path == FlowMode.PILOT:
        next_steps.append(
            "Keep launch on hold until authorized reviewers approve private "
            "evidence outside this repository."
        )
    stage_order = {
        FlowMode.DEMO: (FlowStage.DEMO,),
        FlowMode.SANDBOX: (
            FlowStage.DEMO,
            FlowStage.SANDBOX_PREFLIGHT,
            FlowStage.SANDBOX_ONBOARDING,
            FlowStage.SANDBOX_SMOKE,
            FlowStage.SANDBOX_VALIDATION,
        ),
        FlowMode.PILOT: tuple(FlowStage),
    }
    stage_statuses = {
        FlowStage.DEMO: profile.demo_status,
        FlowStage.SANDBOX_PREFLIGHT: profile.dmsa_refs_status,
        FlowStage.SANDBOX_ONBOARDING: profile.allowed_scope_status,
        FlowStage.SANDBOX_SMOKE: profile.sandbox_smoke_status,
        FlowStage.SANDBOX_VALIDATION: profile.permission_review_status,
        FlowStage.PILOT_PREFLIGHT: profile.pilot_readiness_status,
        FlowStage.PILOT_APPROVAL: profile.pilot_approval_status,
        FlowStage.PILOT_LAUNCH_HOLD: FlowStatus.NEEDS_REVIEW,
    }
    milestones = [
        FlowMilestone(
            stage=stage,
            status=stage_statuses[stage],
            message=f"{stage.value.replace('_', ' ').title()} milestone.",
        )
        for stage in stage_order[profile.selected_path]
    ]
    return FlowReadinessReport(
        profile_name=profile.profile_name,
        selected_path=profile.selected_path,
        decision=decision,
        status=status,
        requirements=requirements,
        milestones=milestones,
        findings=findings,
        next_steps=next_steps,
    )


def build_default_flow_template(selected_path: FlowMode | str, settings: Settings) -> FlowProfile:
    try:
        mode = FlowMode(selected_path)
    except ValueError as exc:
        raise SandboxPilotFlowBlockedError("Unsupported flow path.") from exc
    profile = FlowProfile(profile_name=f"Example {mode.value.title()} Flow", selected_path=mode)
    if mode == FlowMode.DEMO:
        return profile
    updates = {"demo_status": FlowStatus.READY}
    if mode == FlowMode.SANDBOX:
        updates.update(
            {
                name: FlowStatus.NEEDS_CONFIGURATION
                for name in (
                    "dmsa_refs_status",
                    "admin_auth_status",
                    "allowed_scope_status",
                    "permission_review_status",
                    "sandbox_smoke_status",
                    "webhook_review_status",
                )
            }
        )
    return profile.model_copy(update=updates)


def render_sandbox_to_pilot_plan(profile: FlowProfile, report: FlowReadinessReport) -> str:
    return """# Demo → Sandbox → Pilot plan

1. Run the credential-free fixture demo and local doctor.
2. Create the ignored private workspace.
3. Configure private DMSA refs, allowed scope, admin authentication, and permission review.
4. Run the sandbox smoke harness only through its separate manual gate;
   store only a private result reference.
5. Validate secret, storage, PostgreSQL, deployment, diagnostics,
   evidence-review, backup, and rollback readiness.
6. Prepare the private approval packet and keep launch on hold for authorized human review.

This plan makes no external calls and does not approve or deploy a pilot.
"""


def _checklist(title: str, requirements: list[FlowRequirement]) -> str:
    lines = [
        f"# {title}",
        "",
        "Local readiness only; no external calls or approval are performed.",
        "",
    ]
    lines += [
        f"- [{'x' if r.status == FlowStatus.READY else ' '}] {r.requirement}: {r.message}"
        for r in requirements
    ]
    return "\n".join(lines) + "\n"


def render_sandbox_onboarding_checklist(profile: FlowProfile, report: FlowReadinessReport) -> str:
    return _checklist(
        "Sandbox onboarding checklist",
        [r for r in report.requirements if r.stage != FlowStage.PILOT_PREFLIGHT],
    )


def render_pilot_preflight_checklist(profile: FlowProfile, report: FlowReadinessReport) -> str:
    return _checklist(
        "Pilot preflight checklist",
        report.requirements if profile.selected_path == FlowMode.PILOT else [],
    )


def render_flow_summary(profile: FlowProfile, report: FlowReadinessReport) -> str:
    return (
        f"# Flow summary\n\nPath: `{profile.selected_path.value}`\n\n"
        f"Decision: `{report.decision.value}`\n\n"
        "Pilot approved: **no**. External calls: **none**.\n"
    )


def write_sandbox_pilot_flow_artifacts(
    profile: FlowProfile, output_root: Path
) -> FlowArtifactResult:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise SandboxPilotFlowBlockedError("Unsafe output root.")
    report = build_sandbox_pilot_flow_report(profile, Settings(_env_file=None))
    if report.status == FlowStatus.BLOCKED:
        raise SandboxPilotFlowBlockedError("Flow profile is blocked.")
    slug = re.sub(r"[^a-z0-9]+", "-", profile.profile_name.casefold()).strip("-")
    if not slug:
        raise SandboxPilotFlowBlockedError("Unsafe profile name.")
    target = output_root / slug
    target.mkdir(parents=True, exist_ok=False)
    documents = {
        "flow-report.json": report.model_dump_json(indent=2) + "\n",
        "flow-summary.md": render_flow_summary(profile, report),
        "sandbox-to-pilot-plan.md": render_sandbox_to_pilot_plan(profile, report),
        "sandbox-onboarding-checklist.md": render_sandbox_onboarding_checklist(profile, report),
        "pilot-preflight-checklist.md": render_pilot_preflight_checklist(profile, report),
        "launch-hold.md": (
            "# Launch hold\n\nNo pilot is approved. Keep launch on hold pending "
            "authorized private review.\n"
        ),
    }
    documents["manifest.json"] = (
        json.dumps(
            {
                "profile_name": profile.profile_name,
                "files": list(ARTIFACTS),
                "external_calls": False,
                "pilot_approved": False,
            },
            indent=2,
        )
        + "\n"
    )
    for name, content in documents.items():
        (target / name).write_text(content)
    return FlowArtifactResult(
        profile_name=profile.profile_name,
        output_directory=f"{output_root.name}/{slug}",
        files=list(ARTIFACTS),
    )

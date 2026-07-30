import json

from app.config import Settings
from app.schemas.sandbox_smoke_ux import (
    SandboxSmokeCommandSummary,
    SandboxSmokeEvidenceRefTemplate,
    SandboxSmokeOutputPolicy,
    SandboxSmokeUxChecklist,
    SandboxSmokeUxFinding,
    SandboxSmokeUxPlan,
    SandboxSmokeUxRequirement,
    SandboxSmokeUxStatus,
)
from app.services.sandbox_smoke import MAX_SANDBOX_SMOKE_RECORDS

LIVE_COMMAND_NAME = "python scripts/run_sandbox_dmsa_smoke.py"


def build_sandbox_smoke_ux_plan(settings: Settings) -> SandboxSmokeUxPlan:
    requirements = (
        SandboxSmokeUxRequirement(
            name="manual_enablement",
            configured=settings.sandbox_smoke_enabled,
            guidance="Enable only for an explicitly authorized manual run.",
        ),
        SandboxSmokeUxRequirement(
            name="sandbox_target",
            configured=settings.procore_environment == "sandbox",
            guidance="The private Procore target must be sandbox.",
        ),
        SandboxSmokeUxRequirement(
            name="live_mode_gate",
            configured=settings.procore_live_mode_enabled,
            guidance="The separate live-mode gate is required only for the manual run.",
        ),
        SandboxSmokeUxRequirement(
            name="dmsa_secret_references",
            configured=False,
            guidance="Configure DMSA client and secret refs in the private connection profile.",
        ),
        SandboxSmokeUxRequirement(
            name="allowed_company_scope",
            configured=bool(settings.sandbox_smoke_company_id),
            guidance="Configure an authorized private company-scope reference.",
        ),
        SandboxSmokeUxRequirement(
            name="allowed_project_scope",
            configured=bool(settings.sandbox_smoke_project_id),
            guidance="Configure an authorized private project allowlist reference.",
        ),
        SandboxSmokeUxRequirement(
            name="manual_confirmation",
            configured=settings.sandbox_smoke_require_confirmation,
            guidance="Keep the exact read-only sandbox confirmation gate enabled.",
        ),
    )
    findings: list[SandboxSmokeUxFinding] = []
    if not settings.sandbox_smoke_enabled:
        findings.append(
            SandboxSmokeUxFinding(
                code="manual_gate_disabled",
                status=SandboxSmokeUxStatus.NEEDS_CONFIGURATION,
                message="Live smoke remains disabled, which is safe for planning.",
            )
        )
    unsafe = (
        settings.sandbox_smoke_allow_production
        or settings.sandbox_smoke_attachment_downloads
        or not settings.sandbox_smoke_require_confirmation
        or settings.sandbox_smoke_max_records > MAX_SANDBOX_SMOKE_RECORDS
    )
    if unsafe:
        findings.append(
            SandboxSmokeUxFinding(
                code="unsafe_posture",
                status=SandboxSmokeUxStatus.BLOCKED,
                message="One or more mandatory sandbox smoke safety controls are unsafe.",
                fail_level=True,
            )
        )
    missing = any(not item.configured for item in requirements)
    status = (
        SandboxSmokeUxStatus.BLOCKED
        if unsafe
        else (
            SandboxSmokeUxStatus.NEEDS_CONFIGURATION
            if missing
            else SandboxSmokeUxStatus.READY_FOR_PRIVATE_CONFIGURATION
        )
    )
    checklist = SandboxSmokeUxChecklist(
        status=status,
        requirements=requirements,
        findings=tuple(findings),
    )
    return SandboxSmokeUxPlan(
        status=status,
        summary=(
            "Offline preflight only. The live read-only smoke command remains separate "
            "and manually gated."
        ),
        checklist=checklist,
        command=SandboxSmokeCommandSummary(
            planning_command="make sandbox-smoke-preflight",
            live_command_name=LIVE_COMMAND_NAME,
            confirmation_phrase=settings.sandbox_smoke_confirmation_phrase,
        ),
        output_policy=SandboxSmokeOutputPolicy(
            guidance=(
                "Live output is sanitized. Store only a private evidence reference outside Git; "
                "never copy report contents into the public repository."
            )
        ),
        what_it_checks=(
            "DMSA authentication through private secret references",
            "Access to the explicitly allowed sandbox project",
            "Bounded read-only RFI and Submittal samples",
            "Visible attachment metadata counts without downloads",
        ),
        what_it_does_not_do=(
            "Write, update, approve, upload, or delete anything in Procore",
            "Register or change webhooks",
            "Download attachments by default",
            "Persist raw Procore payloads, identifiers, URLs, or secret values",
            "Run from quality, doctor, prepare-sandbox, walkthroughs, or default targets",
        ),
    )


def build_sandbox_smoke_evidence_template() -> SandboxSmokeEvidenceRefTemplate:
    return SandboxSmokeEvidenceRefTemplate(
        smoke_ref="SANDBOX_SMOKE_REF_PLACEHOLDER",
        run_label="SANDBOX_SMOKE_RUN_LABEL_PLACEHOLDER",
        company_scope_ref="SANDBOX_COMPANY_SCOPE_REF_PLACEHOLDER",
        project_scope_ref="SANDBOX_PROJECT_SCOPE_REF_PLACEHOLDER",
        result_status="SANDBOX_SMOKE_RESULT_STATUS_PLACEHOLDER",
        reviewer_placeholder="SANDBOX_SMOKE_REVIEWER_PLACEHOLDER",
        expiry_placeholder="SANDBOX_SMOKE_EXPIRY_PLACEHOLDER",
    )


def render_sandbox_smoke_preflight(plan: SandboxSmokeUxPlan) -> str:
    lines = [
        "Sandbox smoke preflight — OFFLINE ONLY",
        "======================================",
        f"Status: {plan.status.value}",
        plan.summary,
        "",
        "Private configuration checklist:",
    ]
    for requirement in plan.checklist.requirements:
        state = "configured" if requirement.configured else "needs private configuration"
        lines.append(f"- {requirement.name}: {state}. {requirement.guidance}")
    lines.extend(
        (
            "",
            f"Manual live command name: {plan.command.live_command_name}",
            "Do not run it until private configuration, authorization, and every gate are ready.",
            "This preflight resolves no credentials and makes no Procore or external calls.",
        )
    )
    return "\n".join(lines) + "\n"


def render_sandbox_smoke_explanation(plan: SandboxSmokeUxPlan) -> str:
    lines = [
        "Manually gated sandbox smoke",
        "============================",
        "This is a bounded, read-only Procore sandbox check. It is never automatic.",
        f"Live command name: {plan.command.live_command_name}",
        f"Required confirmation phrase: {plan.command.confirmation_phrase}",
        "",
        "What it checks:",
        *(f"- {item}" for item in plan.what_it_checks),
        "",
        "What it does not do:",
        *(f"- {item}" for item in plan.what_it_does_not_do),
        "",
        "Output and evidence:",
        f"- {plan.output_policy.guidance}",
        "- Use `make sandbox-smoke-evidence-template` for placeholder-only private metadata.",
    ]
    return "\n".join(lines) + "\n"


def render_sandbox_smoke_evidence_template() -> str:
    template = build_sandbox_smoke_evidence_template()
    return json.dumps(template.model_dump(mode="json"), indent=2) + "\n"

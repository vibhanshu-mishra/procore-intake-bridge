import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings
from app.schemas.usage_modes import (
    DemoModeReadiness,
    ModeArtifactResult,
    ModeCommandHint,
    ModeQuickstartStep,
    PilotModeReadiness,
    SandboxModeReadiness,
    UsageMode,
    UsageModeDoctorReport,
    UsageModeFinding,
    UsageModeRequirement,
    UsageModeStatus,
)
from app.security.admin_access import effective_admin_auth_mode

SENSITIVE = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|(?:secret|token|password|signature)"
    r"\s*[:=]\s*\S+)"
)
ABSOLUTE_PATH = re.compile(r"(?i)(?:^|[\s\"'])(?:/Users/|/home/|/private/|/tmp/|/var/|[A-Z]:\\)")
SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires)=")
DATABASE_URL = re.compile(r"(?i)\b(?:sqlite|postgres(?:ql)?|mysql|mariadb|mongodb)://")
SAFE_OUTPUT_NAMES = {"mode-report.json", "mode-report.md", "manifest.json"}


class UsageModeError(RuntimeError):
    """A sanitized local usage-mode operation failed."""


class UsageModeBlockedError(UsageModeError):
    """A fail-closed mode doctor safety gate blocked execution."""


def sanitize_mode_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(term in normalized for term in ("authorization", "secret_value", "token_value")):
                sanitized[str(key)] = "[redacted]"
            else:
                sanitized[str(key)] = sanitize_mode_value(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_mode_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if SENSITIVE.search(value):
            return "[redacted]"
        if ABSOLUTE_PATH.search(value):
            return "[redacted-path]"
        parsed = urlsplit(value)
        if parsed.scheme and (
            parsed.username or parsed.password or parsed.query or parsed.fragment
        ):
            return "[redacted-url]"
    return value


def get_selected_usage_mode(settings: Settings) -> UsageMode:
    allowed = {
        item.strip().casefold()
        for item in settings.allowed_usage_modes.split(",")
        if item.strip()
    }
    try:
        selected = UsageMode(settings.usage_mode)
    except ValueError as exc:
        raise UsageModeBlockedError("Usage mode is invalid and fails closed.") from exc
    if selected.value not in allowed:
        raise UsageModeBlockedError("Selected usage mode is not allowed.")
    return selected


def _requirement(
    requirement: str, satisfied: bool, detail: str, *, required: bool = True
) -> UsageModeRequirement:
    return UsageModeRequirement(
        requirement=requirement,
        satisfied=satisfied,
        required=required,
        detail=detail,
    )


def _status(
    enabled: bool, requirements: list[UsageModeRequirement]
) -> UsageModeStatus:
    if not enabled:
        return UsageModeStatus.UNAVAILABLE
    if any(item.required and not item.satisfied for item in requirements):
        return UsageModeStatus.NEEDS_CONFIGURATION
    return UsageModeStatus.READY


def _file_available(path: str) -> bool:
    return Path(path).is_file()


def build_demo_mode_readiness(
    settings: Settings, db_session=None
) -> DemoModeReadiness:
    requirements = [
        _requirement(
            "app_imports",
            True,
            "The application configuration and mode service import locally.",
        ),
        _requirement(
            "fixture_mode",
            settings.procore_mode == "fixture" and not settings.procore_live_mode_enabled,
            "Fixture mode is selected and live mode is off.",
        ),
        _requirement(
            "fixture_data",
            _file_available("app/fixtures/fake_rfis.json")
            and _file_available("app/fixtures/fake_submittals.json"),
            "Committed synthetic RFI and submittal fixtures are available.",
        ),
        _requirement(
            "local_database",
            settings.database_provider == "sqlite" and settings.database_allow_sqlite,
            "SQLite is available for Demo; no external database is required.",
        ),
        _requirement(
            "demo_scripts",
            _file_available("scripts/run_poll_once.py")
            and _file_available("scripts/print_operator_diagnostics.py"),
            "Safe fixture dry-run and diagnostics commands are available.",
        ),
    ]
    status = _status(settings.demo_mode_enabled, requirements)
    findings = [
        UsageModeFinding(
            code="demo_credentials",
            status=UsageModeStatus.READY,
            message="Demo mode requires no Procore credentials or secrets.",
        ),
        UsageModeFinding(
            code="demo_external_services",
            status=UsageModeStatus.READY,
            message="Demo mode requires no cloud or external services.",
        ),
        UsageModeFinding(
            code="demo_storage",
            status=UsageModeStatus.READY,
            message="Storage is optional for the basic demo; local private storage is available.",
        ),
    ]
    return DemoModeReadiness(
        status=status,
        summary=(
            "Demo mode is ready for local fixture use."
            if status == UsageModeStatus.READY
            else "Demo mode needs local repository setup."
        ),
        requirements=requirements,
        findings=findings,
        quickstart_steps=[
            ModeQuickstartStep(order=1, title="Check setup", instruction="Run `make check-local`."),
            ModeQuickstartStep(order=2, title="Run demo", instruction="Run `make demo`."),
            ModeQuickstartStep(
                order=3, title="Inspect diagnostics", instruction="Run `make diagnostics`."
            ),
        ],
        command_hints=[
            ModeCommandHint(mode="demo", purpose="Local setup", command="make check-local"),
            ModeCommandHint(mode="demo", purpose="Fixture demo", command="make demo"),
            ModeCommandHint(mode="demo", purpose="Fixture dry-run", command="make demo-sync"),
        ],
        secrets_required=False,
        external_services_required=False,
    )


def _sandbox_connection_posture(db_session) -> tuple[bool, bool]:
    if db_session is None:
        return False, False
    try:
        from app.models import DMSAConnection

        connections = db_session.query(DMSAConnection).all()
    except Exception:
        return False, False
    refs = any(item.client_id_ref and item.secret_name for item in connections)
    scopes = any(
        item.procore_company_id and item.permitted_project_ids for item in connections
    )
    return refs, scopes


def build_sandbox_mode_readiness(
    settings: Settings, db_session=None
) -> SandboxModeReadiness:
    refs_present, scopes_present = _sandbox_connection_posture(db_session)
    requirements = [
        _requirement(
            "sandbox_target",
            settings.procore_environment == "sandbox",
            "The Procore target must be configured as sandbox.",
        ),
        _requirement(
            "dmsa_secret_references",
            refs_present,
            "Configure DMSA secret references privately; values are never reported.",
        ),
        _requirement(
            "allowed_scope",
            scopes_present
            or bool(
                settings.sandbox_smoke_company_id
                and settings.sandbox_smoke_project_id
            ),
            "Configure private allowed company and project scope.",
        ),
        _requirement(
            "manual_smoke_harness",
            _file_available("scripts/run_sandbox_dmsa_smoke.py")
            and settings.sandbox_smoke_require_confirmation,
            "The existing sandbox smoke harness remains manually confirmed and gated.",
        ),
        _requirement(
            "attachment_downloads_off",
            not settings.sandbox_smoke_attachment_downloads,
            "Sandbox smoke attachment downloads remain disabled.",
        ),
        _requirement(
            "admin_auth",
            effective_admin_auth_mode(settings) in {"token_required", "local_optional"},
            "Admin authentication posture is configured; token mode is recommended.",
            required=False,
        ),
        _requirement(
            "webhook_verification_tools",
            _file_available("scripts/print_webhook_verification_plan.py")
            and _file_available("scripts/check_webhook_docs_record.py"),
            "Offline webhook documentation and verification planning tools are available.",
        ),
        _requirement(
            "private_workspace_tools",
            _file_available("scripts/init_private_workspace.py")
            and _file_available("scripts/validate_private_workspace.py"),
            "Ignored private workspace bootstrap and validation tools are available.",
        ),
        _requirement(
            "secret_provider",
            settings.secret_provider
            in {
                "env",
                "file",
                "aws_secrets_manager",
                "azure_key_vault",
                "gcp_secret_manager",
            },
            "A real env, file, or privately verified optional cloud provider is selected.",
        ),
        _requirement(
            "storage_provider",
            settings.storage_provider
            in {"local", "s3", "azure_blob", "gcs"},
            "Local or optional cloud storage posture is selected; attachments stay metadata-first.",
        ),
    ]
    status = _status(settings.sandbox_mode_enabled, requirements)
    return SandboxModeReadiness(
        status=status,
        summary=(
            "Sandbox planning prerequisites are configured."
            if status == UsageModeStatus.READY
            else "Sandbox mode needs private DMSA references and sandbox scope configuration."
        ),
        requirements=requirements,
        findings=[
            UsageModeFinding(
                code="sandbox_live_gate",
                status=(
                    UsageModeStatus.READY
                    if not settings.procore_live_mode_enabled
                    else UsageModeStatus.NEEDS_CONFIGURATION
                ),
                message=(
                    "Live mode remains off; a real smoke run requires separate explicit opt-in."
                    if not settings.procore_live_mode_enabled
                    else "Live mode is explicitly enabled, but no call is made by this check."
                ),
            ),
            UsageModeFinding(
                code="sandbox_storage_guidance",
                status=UsageModeStatus.READY,
                message=(
                    "Keep attachments metadata-only first; cloud storage is never contacted "
                    "by this check."
                ),
            ),
            UsageModeFinding(
                code="sandbox_automatic_calls",
                status=UsageModeStatus.READY,
                message="Sandbox readiness performs no automatic Procore calls.",
            ),
            UsageModeFinding(
                code="sandbox_secret_provider_guidance",
                status=UsageModeStatus.READY,
                message=(
                    "Use env refs for the simplest sandbox setup or file refs for an "
                    "ignored local private workspace."
                ),
            ),
        ],
        quickstart_steps=[
            ModeQuickstartStep(
                order=1,
                title="Private configuration",
                instruction="Run `make init-private-workspace` for ignored sandbox placeholders.",
            ),
            ModeQuickstartStep(
                order=2,
                title="Review plan",
                instruction="Run `make sandbox-check`; it makes no Procore call.",
            ),
            ModeQuickstartStep(
                order=3,
                title="Optional manual probe",
                instruction="Separately run the documented gated smoke command when authorized.",
            ),
        ],
        command_hints=[
            ModeCommandHint(
                mode="sandbox",
                purpose="Readiness planning",
                command="make sandbox-check",
            ),
            ModeCommandHint(
                mode="sandbox",
                purpose="Print smoke plan",
                command="python scripts/print_sandbox_smoke_plan.py",
            ),
            ModeCommandHint(
                mode="sandbox",
                purpose="Explicit gated smoke",
                command="python scripts/run_sandbox_dmsa_smoke.py --help",
                may_call_procore=True,
                requires_explicit_gate=True,
            ),
        ],
        secrets_required=True,
        external_services_required=True,
        smoke_test_manual=True,
        attachment_downloads_enabled=settings.sandbox_smoke_attachment_downloads,
    )


PILOT_TOOLS = {
    "customer_deployment": "scripts/validate_customer_deployment_profile.py",
    "private_evidence": "scripts/validate_private_evidence_manifest.py",
    "evidence_review": "scripts/validate_evidence_review.py",
    "evidence_expiry": "scripts/check_evidence_expiry.py",
    "pilot_readiness": "scripts/validate_pilot_readiness.py",
    "pilot_approval": "scripts/validate_pilot_approval_packet.py",
    "approval_safety": "scripts/check_pilot_approval_safety.py",
    "support_diagnostics": "scripts/print_operator_diagnostics.py",
    "private_workspace_tools": "scripts/validate_private_workspace.py",
}


def build_pilot_mode_readiness(
    settings: Settings, db_session=None
) -> PilotModeReadiness:
    tool_requirements = [
        _requirement(
            name,
            _file_available(path),
            f"The local {name.replace('_', ' ')} capability is available.",
        )
        for name, path in PILOT_TOOLS.items()
    ]
    requirements = [
        *tool_requirements,
        _requirement(
            "admin_auth_posture",
            effective_admin_auth_mode(settings) != "disabled",
            "Admin authentication is enabled; token-required mode is needed for nonlocal use.",
        ),
        _requirement(
            "secret_provider_posture",
            settings.secret_provider
            not in {"disabled", "test", "external_placeholder"},
            "A real secret provider is selected without resolving or displaying values.",
        ),
        _requirement(
            "storage_provider_posture",
            settings.storage_provider
            not in {"disabled", "test", "external_placeholder"},
            "A local or optional cloud storage posture is selected without contacting it.",
        ),
        _requirement(
            "migration_posture",
            settings.migration_check_enabled and not settings.auto_run_migrations,
            "Migration checks are enabled and automatic migration remains off.",
        ),
        _requirement(
            "database_provider_posture",
            settings.database_provider == "postgres"
            or not settings.postgres_required_for_pilot,
            "PostgreSQL and a private URL reference are required for Pilot.",
        ),
        _requirement(
            "deployment_recipe_posture",
            settings.deployment_recipes_enabled
            and not settings.deployment_external_provisioning_enabled,
            "Deployment recipes and runbooks are available without executing deployment.",
        ),
        _requirement(
            "rollback_backup_guidance",
            _file_available("docs/database-migrations.md")
            and _file_available("docs/pilot-approval-packet.md"),
            "Rollback and backup guidance is available.",
        ),
        _requirement(
            "private_workspace",
            False,
            "Initialize and privately complete the ignored workspace outside GitHub.",
        ),
    ]
    status = _status(settings.pilot_mode_enabled, requirements)
    return PilotModeReadiness(
        status=status,
        summary=(
            "Pilot tooling is available, but private workspace and approvals remain operator work."
            if status == UsageModeStatus.NEEDS_CONFIGURATION
            else "Pilot mode planning prerequisites are ready."
        ),
        requirements=requirements,
        findings=[
            UsageModeFinding(
                code="pilot_public_evidence",
                status=UsageModeStatus.READY,
                message="No real evidence or approval is required in the public repository.",
            ),
            UsageModeFinding(
                code="pilot_approval",
                status=UsageModeStatus.NEEDS_CONFIGURATION,
                message="Private evidence and real approval must be supplied outside this repo.",
            ),
        ],
        quickstart_steps=[
            ModeQuickstartStep(
                order=1,
                title="Validate fake tools",
                instruction="Run `make pilot-check`.",
            ),
            ModeQuickstartStep(
                order=2,
                title="Create private workspace",
                instruction="Run `make init-private-workspace`, then fill placeholders privately.",
            ),
            ModeQuickstartStep(
                order=3,
                title="Private decision",
                instruction="Review readiness, expiry, rollback, and approval privately.",
            ),
        ],
        command_hints=[
            ModeCommandHint(mode="pilot", purpose="Pilot validators", command="make pilot-check"),
            ModeCommandHint(mode="pilot", purpose="Diagnostics", command="make diagnostics"),
            ModeCommandHint(
                mode="pilot",
                purpose="Approval safety",
                command="make pilot-approval-safety-check",
            ),
        ],
        secrets_required=True,
        external_services_required=True,
        private_evidence_required_in_repo=False,
        real_approval_recorded=False,
    )


def build_usage_mode_doctor_report(
    settings: Settings, db_session=None
) -> UsageModeDoctorReport:
    if not settings.mode_doctor_enabled:
        raise UsageModeBlockedError("Mode doctor is disabled.")
    selected = get_selected_usage_mode(settings)
    demo = build_demo_mode_readiness(settings, db_session)
    sandbox = build_sandbox_mode_readiness(settings, db_session)
    pilot = build_pilot_mode_readiness(settings, db_session)
    if not settings.mode_doctor_include_demo:
        demo.status = UsageModeStatus.SKIPPED
    if not settings.mode_doctor_include_sandbox:
        sandbox.status = UsageModeStatus.SKIPPED
    if not settings.mode_doctor_include_pilot:
        pilot.status = UsageModeStatus.SKIPPED
    selected_readiness = {
        UsageMode.DEMO: demo,
        UsageMode.SANDBOX: sandbox,
        UsageMode.PILOT: pilot,
    }[selected]
    next_steps = [
        step.instruction for step in selected_readiness.quickstart_steps
    ]
    report = UsageModeDoctorReport(
        generated_at=datetime.now(UTC),
        selected_mode=selected,
        selected_mode_status=selected_readiness.status,
        demo=demo,
        sandbox=sandbox,
        pilot=pilot,
        recommended_next_steps=next_steps,
        command_hints=[
            *demo.command_hints,
            *sandbox.command_hints,
            *pilot.command_hints,
        ],
        safety_boundaries=[
            "The doctor performs local configuration checks only.",
            "It never resolves or prints secret values.",
            "It makes no Procore or external service calls.",
            "Sandbox smoke remains a separate explicitly gated command.",
            "Pilot evidence and approvals remain private and outside GitHub.",
            "No mode is a production security or deployment approval.",
        ],
    )
    validate_usage_mode_report_safe(report)
    return report


def render_usage_mode_report_markdown(report: UsageModeDoctorReport) -> str:
    lines = [
        "# Procore Intake Bridge mode doctor",
        "",
        f"Selected mode: **{report.selected_mode.value}**",
        f"Selected status: **{report.selected_mode_status.value}**",
        "",
    ]
    for readiness in (report.demo, report.sandbox, report.pilot):
        lines.extend(
            [
                f"## {readiness.mode.value.title()} mode — {readiness.status.value}",
                "",
                readiness.summary,
                "",
            ]
        )
        lines.extend(
            f"- {'Ready' if item.satisfied else 'Missing'}: {item.detail}"
            for item in readiness.requirements
        )
        lines.append("")
    lines.extend(["## Recommended next steps", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(report.recommended_next_steps, 1))
    lines.extend(["", "## Safety boundaries", ""])
    lines.extend(f"- {boundary}" for boundary in report.safety_boundaries)
    return "\n".join(lines) + "\n"


def validate_usage_mode_report_safe(report: UsageModeDoctorReport) -> None:
    payload = json.dumps(report.model_dump(mode="json"), sort_keys=True)
    if (
        report.values_exposed
        or report.external_calls
        or report.procore_calls
        or report.file_contents_included
        or report.local_paths_included
        or SENSITIVE.search(payload)
        or ABSOLUTE_PATH.search(payload)
        or SIGNED_URL.search(payload)
        or DATABASE_URL.search(payload)
    ):
        raise UsageModeBlockedError("Mode report failed strict sanitized safety validation.")


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise UsageModeBlockedError("Mode report generation blocked: unsafe output root.")
    if not output_root.is_absolute() and output_root.parts[0] not in {
        "mode-output",
        "quickstart-output",
        "doctor-output",
    }:
        raise UsageModeBlockedError(
            "Mode report generation blocked: use a dedicated output root."
        )
    return output_root.resolve()


def write_usage_mode_report(
    report: UsageModeDoctorReport, output_root: Path
) -> ModeArtifactResult:
    validate_usage_mode_report_safe(report)
    root = _safe_output_root(Path(output_root))
    target = (root / report.selected_mode.value).resolve()
    if target.parent != root:
        raise UsageModeBlockedError("Mode report generation blocked: path traversal.")
    target.mkdir(parents=True, exist_ok=False)
    files = {
        "mode-report.json": json.dumps(
            sanitize_mode_value(report.model_dump(mode="json")),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        "mode-report.md": render_usage_mode_report_markdown(report),
        "manifest.json": json.dumps(
            {
                "selected_mode": report.selected_mode.value,
                "files": sorted(SAFE_OUTPUT_NAMES),
                "external_calls": False,
                "procore_calls": False,
                "values_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    }
    for name, content in files.items():
        (target / name).write_text(content, encoding="utf-8")
    return ModeArtifactResult(
        selected_mode=report.selected_mode,
        output_directory=report.selected_mode.value,
        files=list(files),
    )

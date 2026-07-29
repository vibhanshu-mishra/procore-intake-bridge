import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.deployment_recipes import (
    DeploymentFinding,
    DeploymentRecipeArtifactResult,
    DeploymentRecipeProfile,
    DeploymentRecipeReadinessReport,
    DeploymentRecipeStatus,
    DeploymentRequirement,
    DeploymentTargetKind,
)

PLACEHOLDER = re.compile(r"(?i)(placeholder|example|fake|sample|not_configured)")
URL = re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mysql|s3|gs|docker)://\S+")
DOMAIN = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud)\b")
SECRET = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|(?:secret|token|password|credential)"
    r"\s*[:=]\s*\S+)"
)
CERTIFICATE = re.compile(
    r"(?i)(-----BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE)|"
    r"certificate_request|private_key)"
)
INFRA_ID = re.compile(
    r"(?i)\b(?:vpc|subnet|lb|arn|subscription|account|project|registry)"
    r"[-_:=/][a-z0-9-]{4,}\b"
)
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\b(?:\+?1[-. ]?)?\d{3}[-. ]\d{3}[-. ]\d{4}\b")
PROCORE_ID = re.compile(r"(?<!\w)\d{6,}(?!\w)")
BLOCKED_FILE = re.compile(
    r"(?i)\.(?:sql|dump|backup|bak|pgdump|pem|key|crt|csr|p12|pfx|tfstate|tfvars|log)\b"
)
SAFE_RECIPE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
ARTIFACT_FILES = [
    "deployment-plan.md",
    "deployment-readiness-report.json",
    "https-tls-checklist.md",
    "webhook-ingress-checklist.md",
    "cutover-checklist.md",
    "backup-runbook.md",
    "rollback-runbook.md",
    "operator-runbook.md",
    "manifest.json",
]


class DeploymentRecipeError(RuntimeError):
    """Deployment recipe operation failed with private details suppressed."""


class DeploymentRecipeBlockedError(DeploymentRecipeError):
    pass


def sanitize_deployment_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_deployment_value(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_deployment_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if URL.search(value):
            return "[masked-url]"
        if SECRET.search(value):
            return "[masked-secret]"
        if CERTIFICATE.search(value):
            return "[masked-certificate]"
        if ABSOLUTE_PATH.search(value):
            return "[masked-path]"
    return value


def _strings(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _finding(code: str, message: str) -> DeploymentFinding:
    return DeploymentFinding(code=code, severity="blocking", message=message)


def validate_deployment_recipe_profile(
    profile: DeploymentRecipeProfile, settings: Settings
) -> list[DeploymentFinding]:
    findings: list[DeploymentFinding] = []
    if not settings.deployment_recipes_enabled:
        findings.append(_finding("recipes_disabled", "Deployment recipes are disabled."))
    allowed = {
        item.strip() for item in settings.deployment_allowed_targets.split(",")
        if item.strip()
    }
    if profile.target_kind not in allowed:
        findings.append(_finding("target", "Deployment target is not allowed."))
    if not SAFE_RECIPE_NAME.fullmatch(profile.recipe_name):
        findings.append(_finding("recipe_name", "Recipe name must be a safe slug."))
    if len(profile.allowed_hosts_placeholders) > 20:
        findings.append(_finding("host_cap", "Allowed host placeholder count exceeds the cap."))
    for value in _strings(profile.model_dump(mode="json")):
        checks = (
            ("raw_url", URL),
            ("real_domain", DOMAIN),
            ("secret", SECRET),
            ("certificate", CERTIFICATE),
            ("infrastructure_id", INFRA_ID),
            ("absolute_path", ABSOLUTE_PATH),
            ("email", EMAIL),
            ("phone", PHONE),
            ("real_id", PROCORE_ID),
            ("blocked_file", BLOCKED_FILE),
        )
        for code, pattern in checks:
            if pattern.search(value):
                findings.append(_finding(code, f"Unsafe {code.replace('_', ' ')} is blocked."))
    required_refs = [
        profile.public_base_url_placeholder,
        *profile.allowed_hosts_placeholders,
        profile.database_url_ref_placeholder,
        profile.secret_provider_ref_placeholder,
        profile.storage_provider_ref_placeholder,
        profile.admin_auth_ref_placeholder,
        profile.webhook_secret_ref_placeholder,
    ]
    if settings.deployment_recipe_require_placeholders and any(
        not PLACEHOLDER.search(value) for value in required_refs
    ):
        findings.append(_finding("placeholders", "Recipe references must be placeholders."))
    if profile.webhooks_planned:
        if (
            settings.deployment_require_https_for_webhooks
            and profile.tls_status != DeploymentRecipeStatus.READY
        ):
            findings.append(_finding("https", "Planned webhooks require reviewed HTTPS posture."))
        if (
            settings.deployment_require_public_ingress_for_webhooks
            and profile.public_ingress_status != DeploymentRecipeStatus.READY
        ):
            findings.append(_finding(
                "public_ingress", "Planned webhooks require reviewed public ingress posture."
            ))
    if profile.environment_label.casefold().startswith(("pilot", "sandbox")):
        required = (
            ("backup", profile.backup_status, settings.deployment_require_backup_plan),
            ("rollback", profile.rollback_status, settings.deployment_require_rollback_plan),
            ("operator_runbook", profile.operator_runbook_status,
             settings.deployment_require_operator_runbook),
        )
        for code, status, enabled in required:
            if enabled and status == DeploymentRecipeStatus.BLOCKED:
                findings.append(_finding(code, f"{code.replace('_', ' ').title()} is required."))
    return findings


def build_deployment_recipe_readiness_report(
    profile: DeploymentRecipeProfile, settings: Settings
) -> DeploymentRecipeReadinessReport:
    findings = validate_deployment_recipe_profile(profile, settings)
    requirements = [
        DeploymentRequirement(
            requirement="external_provisioning",
            status=(
                DeploymentRecipeStatus.BLOCKED
                if settings.deployment_external_provisioning_enabled
                else DeploymentRecipeStatus.READY
            ),
            message="External provisioning remains disabled.",
        ),
        DeploymentRequirement(
            requirement="backup",
            status=profile.backup_status,
            message="Backup plan posture is reference-only.",
        ),
        DeploymentRequirement(
            requirement="rollback",
            status=profile.rollback_status,
            message="Rollback plan posture is reference-only.",
        ),
        DeploymentRequirement(
            requirement="operator_runbook",
            status=profile.operator_runbook_status,
            message="Operator runbook posture is reference-only.",
        ),
    ]
    status = (
        DeploymentRecipeStatus.BLOCKED
        if findings or settings.deployment_external_provisioning_enabled
        else DeploymentRecipeStatus.READY
    )
    return DeploymentRecipeReadinessReport(
        recipe_name=profile.recipe_name,
        target_kind=profile.target_kind,
        status=status,
        requirements=requirements,
        findings=findings,
    )


def build_default_deployment_recipe_template(
    target_kind: DeploymentTargetKind | str, settings: Settings
) -> DeploymentRecipeProfile:
    selected = DeploymentTargetKind(target_kind)
    del settings
    return DeploymentRecipeProfile(
        recipe_name=f"example-{selected.value}-recipe",
        target_kind=selected,
        environment_label="EXAMPLE_ENVIRONMENT_PLACEHOLDER",
        known_limitations=["NO_DEPLOYMENT_AUTOMATION_PLACEHOLDER"],
        notes=["EXAMPLE_PLACEHOLDER_RECIPE_ONLY"],
    )


def _render(title: str, profile: DeploymentRecipeProfile, items: list[str]) -> str:
    lines = [
        f"# {title}", "",
        f"Recipe: `{profile.recipe_name}`",
        f"Target: `{profile.target_kind}`", "",
        "This template performs no deployment or external call.", "",
    ]
    lines.extend(f"- [ ] {item}" for item in items)
    return "\n".join(lines) + "\n"


def render_deployment_plan(profile, report) -> str:
    del report
    return _render("Deployment plan", profile, [
        "Review private environment references.",
        "Validate database, secret, storage, and admin authentication posture.",
        "Complete HTTPS, ingress, backup, rollback, and operator reviews.",
    ])


def render_https_tls_checklist(profile, report) -> str:
    del report
    return _render("HTTPS and TLS checklist", profile, [
        "Use TLS certificate reference placeholder only.",
        "Verify redirect, protocol, renewal, and private-key handling privately.",
    ])


def render_webhook_ingress_checklist(profile, report) -> str:
    del report
    return _render("Webhook ingress checklist", profile, [
        "Require HTTPS and a reviewed public ingress reference.",
        "Verify signature enforcement without registering a webhook.",
    ])


def render_cutover_checklist(profile, report) -> str:
    del report
    return _render("Cutover checklist", profile, [
        "Confirm maintenance window and responsible operator.",
        "Confirm backup, restore, diagnostics, and rollback evidence.",
        "Record a private go/no-go decision.",
    ])


def render_backup_runbook(profile, report) -> str:
    del report
    return _render("Backup runbook", profile, [
        "Use BACKUP_PLAN_REF_PLACEHOLDER.",
        "Keep backup contents and paths outside this repository.",
    ])


def render_rollback_runbook(profile, report) -> str:
    del report
    return _render("Rollback runbook", profile, [
        "Use ROLLBACK_PLAN_REF_PLACEHOLDER.",
        "Define rollback triggers and verification privately.",
    ])


def render_operator_deployment_runbook(profile, report) -> str:
    del report
    return _render("Operator deployment runbook", profile, [
        "Validate the recipe and all private references.",
        "Follow separately approved deployment procedures.",
        "Never treat this generated checklist as deployment approval.",
    ])


def write_deployment_recipe_artifacts(
    profile: DeploymentRecipeProfile, output_root: Path
) -> DeploymentRecipeArtifactResult:
    temporary_absolute = (
        output_root.is_absolute()
        and output_root.name.startswith("procore-intake-bridge-deployment-")
        and (
            output_root.parent == Path("/tmp")
            or "pytest-" in output_root.as_posix()
        )
    )
    if (output_root.is_absolute() and not temporary_absolute) or ".." in output_root.parts:
        raise DeploymentRecipeBlockedError("Deployment output root is unsafe.")
    if (
        not temporary_absolute
        and output_root.parts[:1] not in {("deployment-output",), ("deploy-output",)}
    ):
        raise DeploymentRecipeBlockedError("Deployment output root is not approved.")
    settings = Settings(_env_file=None)
    report = build_deployment_recipe_readiness_report(profile, settings)
    if report.status == DeploymentRecipeStatus.BLOCKED:
        raise DeploymentRecipeBlockedError("Deployment recipe failed safety validation.")
    destination = output_root / profile.recipe_name
    destination.mkdir(parents=True, exist_ok=True)
    renderers = {
        "deployment-plan.md": render_deployment_plan,
        "https-tls-checklist.md": render_https_tls_checklist,
        "webhook-ingress-checklist.md": render_webhook_ingress_checklist,
        "cutover-checklist.md": render_cutover_checklist,
        "backup-runbook.md": render_backup_runbook,
        "rollback-runbook.md": render_rollback_runbook,
        "operator-runbook.md": render_operator_deployment_runbook,
    }
    for name, renderer in renderers.items():
        (destination / name).write_text(renderer(profile, report))
    (destination / "deployment-readiness-report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n"
    )
    (destination / "manifest.json").write_text(json.dumps({
        "files": ARTIFACT_FILES,
        "external_calls": False,
        "deployment_executed": False,
        "values_exposed": False,
    }, indent=2) + "\n")
    return DeploymentRecipeArtifactResult(
        recipe_name=profile.recipe_name,
        output_directory=profile.recipe_name,
        files=ARTIFACT_FILES,
    )

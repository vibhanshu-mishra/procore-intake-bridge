import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.hosted_deployment_templates import (
    HostedDeploymentArtifactResult,
    HostedDeploymentFinding,
    HostedDeploymentPlatform,
    HostedDeploymentRequirement,
    HostedDeploymentStatus,
    HostedDeploymentTemplateProfile,
    HostedDeploymentTemplateReport,
)

PLACEHOLDER = re.compile(r"(?i)(?:placeholder|example|private_adaptation_required)")
SAFE_PLACEHOLDER_VALUE = re.compile(
    r"^[A-Z0-9_-]*(?:PLACEHOLDER|PRIVATE_ADAPTATION_REQUIRED)[A-Z0-9_-]*$"
)
RAW_URL = re.compile(
    r"(?i)\b(?:https?|postgres(?:ql)?|mysql|mariadb|mongodb|docker|s3|gs)://\S+"
)
DOMAIN = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud)\b")
REGISTRY_REF = re.compile(
    r"(?i)(?:\b[a-z0-9.-]+(?::\d+)?/[a-z0-9._/-]+:[a-z0-9._-]+\b|"
    r"\b[a-z0-9._-]+/[a-z0-9._/-]+:[a-z0-9._-]+\b|"
    r"\b[a-z0-9._-]+:(?:latest|v?\d[\w.-]*)\b)"
)
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+|"
    r"(?:secret|token|password|credential)\s*[:=]\s*\S+)"
)
CERTIFICATE = re.compile(
    r"(?i)(?:-----BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE)|"
    r"certificate_request|private_key\s*[:=])"
)
AWS_ID = re.compile(r"(?i)(?:\barn:aws[a-z-]*:\S+|\b\d{12}\b)")
AZURE_ID = re.compile(
    r"(?i)(?:/subscriptions/[0-9a-f-]{20,}|"
    r"\b(?:tenant|subscription|resource)[_-]?id\s*[:=]\s*[0-9a-f-]{16,})"
)
GCP_ID = re.compile(
    r"(?i)(?:\bprojects/[a-z0-9-]{6,}\b|"
    r"\b(?:gcp_)?project[_-]?id\s*[:=]\s*[a-z][a-z0-9-]{5,})"
)
INFRA_ID = re.compile(
    r"(?i)\b(?:vpc|subnet|cluster|service|task|app|resource|infra)"
    r"[-_:=/][a-z0-9-]{6,}\b"
)
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
ENV_VALUE = re.compile(r"(?m)^[A-Z][A-Z0-9_]{2,}\s*=\s*(?!.*PLACEHOLDER)\S+")
BLOCKED_FILE = re.compile(
    r"(?i)\.(?:sql|dump|backup|bak|pgdump|pem|key|crt|csr|p12|pfx|log)\b"
)
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\b(?:\+?1[-. ]?)?\d{3}[-. ]\d{3}[-. ]\d{4}\b")
APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:production[- ]ready|approved for production|pilot approved|"
    r"production approved|security complete)\b"
)
SAFE_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
SAFE_ROOTS = {
    "hosted-deployment-output",
    "hosted-deploy-output",
    "platform-deployment-output",
    "container-deployment-output",
}
ARTIFACT_FILES = [
    "hosted-deployment-report.json",
    "hosted-deployment-plan.md",
    "platform-env-template.md",
    "hosting-checklist.md",
    "operator-runbook.md",
    "manifest.json",
]


class HostedDeploymentTemplateError(RuntimeError):
    """Hosted template operation failed with private details suppressed."""


class HostedDeploymentTemplateBlockedError(HostedDeploymentTemplateError):
    pass


def sanitize_hosted_deployment_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_hosted_deployment_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_hosted_deployment_value(item) for item in value]
    if isinstance(value, Path):
        return "[masked-path]"
    if isinstance(value, str):
        if SAFE_PLACEHOLDER_VALUE.fullmatch(value):
            return value
        for pattern, replacement in (
            (RAW_URL, "[masked-url]"),
            (DOMAIN, "[masked-domain]"),
            (REGISTRY_REF, "[masked-registry-reference]"),
            (SECRET, "[masked-secret]"),
            (CERTIFICATE, "[masked-certificate]"),
            (AWS_ID, "[masked-cloud-identifier]"),
            (AZURE_ID, "[masked-cloud-identifier]"),
            (GCP_ID, "[masked-cloud-identifier]"),
            (INFRA_ID, "[masked-infrastructure-identifier]"),
            (ABSOLUTE_PATH, "[masked-path]"),
            (EMAIL, "[masked-contact]"),
            (PHONE, "[masked-contact]"),
            (APPROVAL_CLAIM, "[masked-claim]"),
        ):
            if pattern.search(value):
                return replacement
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


def _finding(code: str, message: str) -> HostedDeploymentFinding:
    return HostedDeploymentFinding(code=code, message=message)


def validate_hosted_deployment_profile(
    profile: HostedDeploymentTemplateProfile, settings: Settings
) -> list[HostedDeploymentFinding]:
    findings: list[HostedDeploymentFinding] = []
    if not settings.hosted_deployment_templates_enabled:
        findings.append(_finding("templates_disabled", "Hosted templates are disabled."))
    if not settings.hosted_deployment_fail_closed:
        findings.append(_finding("fail_closed", "Hosted template validation must fail closed."))
    if not SAFE_PROFILE_NAME.fullmatch(profile.profile_name):
        findings.append(_finding("profile_name", "Profile name must be a safe slug."))
    unsafe_policy = (
        settings.hosted_deployment_allow_real_domains
        or settings.hosted_deployment_allow_real_infra_ids
        or settings.hosted_deployment_allow_real_registry_refs
        or settings.hosted_deployment_allow_real_cloud_ids
        or settings.hosted_deployment_allow_absolute_paths
    )
    if unsafe_policy:
        findings.append(_finding("unsafe_policy", "Public template value allowances are blocked."))

    checks = (
        ("raw_url", RAW_URL),
        ("real_domain", DOMAIN),
        ("registry_ref", REGISTRY_REF),
        ("secret", SECRET),
        ("certificate", CERTIFICATE),
        ("aws_cloud_id", AWS_ID),
        ("azure_cloud_id", AZURE_ID),
        ("gcp_cloud_id", GCP_ID),
        ("infrastructure_id", INFRA_ID),
        ("absolute_path", ABSOLUTE_PATH),
        ("env_value", ENV_VALUE),
        ("blocked_file", BLOCKED_FILE),
        ("email", EMAIL),
        ("phone", PHONE),
        ("approval_claim", APPROVAL_CLAIM),
    )
    values = list(_strings(profile.model_dump(mode="json")))
    for value in values:
        if SAFE_PLACEHOLDER_VALUE.fullmatch(value):
            continue
        for code, pattern in checks:
            if pattern.search(value):
                findings.append(
                    _finding(code, f"Unsafe {code.replace('_', ' ')} is blocked.")
                )
    if settings.hosted_deployment_require_placeholders:
        required = [
            profile.environment_label,
            profile.container_image_placeholder,
            profile.registry_ref_placeholder,
            profile.public_url_placeholder,
            profile.allowed_hosts_placeholder,
            profile.database_url_ref_placeholder,
            profile.admin_token_ref_placeholder,
            profile.dmsa_client_id_ref_placeholder,
            profile.dmsa_client_secret_ref_placeholder,
            profile.webhook_secret_ref_placeholder,
            profile.secret_provider_placeholder,
            profile.storage_provider_placeholder,
            profile.postgres_runtime_placeholder,
            profile.migration_plan_placeholder,
            profile.backup_plan_placeholder,
            profile.rollback_plan_placeholder,
            profile.tls_https_placeholder,
            profile.webhook_ingress_placeholder,
            profile.health_check_placeholder,
            profile.scaling_placeholder,
            profile.logging_placeholder,
            profile.monitoring_placeholder,
        ]
        if any(not PLACEHOLDER.search(value) for value in required):
            findings.append(
                _finding("placeholders", "All hosted template values must be placeholders.")
            )
    return findings


def build_hosted_deployment_report(
    profile: HostedDeploymentTemplateProfile, settings: Settings
) -> HostedDeploymentTemplateReport:
    findings = validate_hosted_deployment_profile(profile, settings)
    requirements = [
        HostedDeploymentRequirement(
            name=name,
            status=HostedDeploymentStatus.NEEDS_CONFIGURATION,
            message="Complete this requirement privately outside Git.",
        )
        for name in (
            "private_values",
            "https_and_ingress",
            "database_storage_secrets",
            "backup_and_rollback",
            "production_review",
        )
    ]
    return HostedDeploymentTemplateReport(
        profile_name=profile.profile_name,
        platform=profile.platform,
        status=(
            HostedDeploymentStatus.BLOCKED
            if findings
            else HostedDeploymentStatus.NEEDS_CONFIGURATION
        ),
        requirements=requirements,
        findings=findings,
        placeholder_only=not findings,
    )


def build_default_hosted_deployment_profile(
    platform: HostedDeploymentPlatform | str, settings: Settings
) -> HostedDeploymentTemplateProfile:
    del settings
    selected = HostedDeploymentPlatform(platform)
    return HostedDeploymentTemplateProfile(
        profile_name=f"example-{selected.value}-hosted-template",
        platform=selected,
    )


def _header(title: str, profile: HostedDeploymentTemplateProfile) -> list[str]:
    return [
        f"# {title}",
        "",
        f"Profile: `{profile.profile_name}`",
        f"Platform style: `{profile.platform}`",
        "",
        "Placeholder-only private adaptation template. It performs no deployment or cloud call.",
        "",
    ]


def render_hosted_deployment_plan(profile, report) -> str:
    del report
    lines = _header("Hosted deployment plan", profile)
    lines.extend(
        f"- [ ] {item}"
        for item in (
            "Adapt container image and registry placeholders privately.",
            "Configure database, secret, and storage providers privately.",
            "Review HTTPS, webhook ingress, health, scale, logging, and monitoring privately.",
            "Review migration, backup, rollback, and known limitations before manual deployment.",
        )
    )
    return "\n".join(lines) + "\n"


def render_platform_env_template(profile, report) -> str:
    del report
    lines = _header("Platform environment template", profile)
    pairs = {
        "CONTAINER_IMAGE_REF": profile.container_image_placeholder,
        "DATABASE_URL_REF": profile.database_url_ref_placeholder,
        "ADMIN_TOKEN_REF": profile.admin_token_ref_placeholder,
        "WEBHOOK_SECRET_REF": profile.webhook_secret_ref_placeholder,
        "SECRET_PROVIDER_REF": profile.secret_provider_placeholder,
        "STORAGE_PROVIDER_REF": profile.storage_provider_placeholder,
    }
    lines.extend(f"- `{key}={value}`" for key, value in pairs.items())
    return "\n".join(lines) + "\n"


def render_hosting_checklist(profile, report) -> str:
    del report
    lines = _header("Hosting checklist", profile)
    lines.extend(
        f"- [ ] {item}"
        for item in (
            "Keep all real values outside Git.",
            "Complete private HTTPS and webhook-ingress setup.",
            "Validate health, capacity, recovery, and rollback privately.",
            "Obtain independent production and security review.",
        )
    )
    return "\n".join(lines) + "\n"


def render_hosted_operator_runbook(profile, report) -> str:
    del report
    lines = _header("Hosted operator runbook", profile)
    lines.extend(
        f"{index}. {item}"
        for index, item in enumerate(
            (
                "Validate the placeholder profile and private references.",
                "Follow a separately reviewed manual deployment process.",
                "Verify health and ingress without copying logs into this repository.",
                "Use the private rollback plan when its criteria are met.",
            ),
            1,
        )
    )
    return "\n".join(lines) + "\n"


def validate_hosted_deployment_report_safe(
    report: HostedDeploymentTemplateReport,
) -> None:
    text = json.dumps(report.model_dump(mode="json"), sort_keys=True)
    for pattern in (
        RAW_URL,
        DOMAIN,
        REGISTRY_REF,
        SECRET,
        CERTIFICATE,
        AWS_ID,
        AZURE_ID,
        GCP_ID,
        INFRA_ID,
        ABSOLUTE_PATH,
        BLOCKED_FILE,
        EMAIL,
        PHONE,
        APPROVAL_CLAIM,
    ):
        if pattern.search(text):
            raise HostedDeploymentTemplateBlockedError(
                "Hosted deployment report failed safety validation."
            )
    unsafe_flags = (
        report.external_calls,
        report.deployment_executed,
        report.cloud_resources_created,
        report.registry_accessed,
        report.images_pushed,
        report.dns_changes_made,
        report.certificates_issued,
        report.private_values_exposed,
        report.infrastructure_ids_exposed,
        report.cloud_ids_exposed,
        report.registry_refs_exposed,
        report.domains_exposed,
        report.local_paths_exposed,
    )
    if any(unsafe_flags):
        raise HostedDeploymentTemplateBlockedError(
            "Hosted deployment report contains unsafe operation flags."
        )


def write_hosted_deployment_artifacts(
    profile: HostedDeploymentTemplateProfile, output_root: Path
) -> HostedDeploymentArtifactResult:
    temporary_absolute = (
        output_root.is_absolute()
        and output_root.name.startswith("procore-intake-bridge-hosted-deployment-")
        and (
            output_root.parent == Path("/tmp")
            or "pytest-" in output_root.as_posix()
        )
    )
    if ".." in output_root.parts or (output_root.is_absolute() and not temporary_absolute):
        raise HostedDeploymentTemplateBlockedError("Hosted deployment output root is unsafe.")
    if not temporary_absolute and output_root.parts[:1] not in {
        (name,) for name in SAFE_ROOTS
    }:
        raise HostedDeploymentTemplateBlockedError(
            "Hosted deployment output root is not approved."
        )
    settings = Settings(_env_file=None)
    report = build_hosted_deployment_report(profile, settings)
    if report.status == HostedDeploymentStatus.BLOCKED:
        raise HostedDeploymentTemplateBlockedError(
            "Hosted deployment profile failed safety validation."
        )
    validate_hosted_deployment_report_safe(report)
    destination = output_root / profile.profile_name
    destination.mkdir(parents=True, exist_ok=True)
    rendered = {
        "hosted-deployment-report.json": (
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        ),
        "hosted-deployment-plan.md": render_hosted_deployment_plan(profile, report),
        "platform-env-template.md": render_platform_env_template(profile, report),
        "hosting-checklist.md": render_hosting_checklist(profile, report),
        "operator-runbook.md": render_hosted_operator_runbook(profile, report),
        "manifest.json": json.dumps(
            {
                "files": ARTIFACT_FILES,
                "external_calls": False,
                "deployment_executed": False,
                "placeholder_only": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    }
    for name, content in rendered.items():
        (destination / name).write_text(content, encoding="utf-8")
    return HostedDeploymentArtifactResult(
        profile_name=profile.profile_name,
        output_directory=profile.profile_name,
        files=ARTIFACT_FILES,
    )

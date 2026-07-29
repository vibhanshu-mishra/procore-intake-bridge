import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings
from app.schemas.customer_deployment import (
    CustomerDeploymentArtifactResult,
    CustomerDeploymentProfile,
    CustomerDeploymentReadinessFinding,
    CustomerDeploymentReadinessReport,
)

PLACEHOLDER_MARKERS = ("example", "fake", "placeholder", "sample", "demo")
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|secret\s*[:=]|token\s*[:=]|signature\s*[:=])"
)
NUMERIC_ID_PATTERN = re.compile(r"^\d{4,}$")
SAFE_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_./:-]{4,200}$")


class CustomerDeploymentError(RuntimeError):
    """A sanitized customer deployment planning operation failed."""


class CustomerDeploymentBlockedError(CustomerDeploymentError):
    """A fail-closed customer profile or artifact gate blocked execution."""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def sanitize_customer_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            is_reference = normalized.endswith(("_ref", "_refs"))
            if not is_reference and any(
                marker in normalized
                for marker in ("authorization", "secret", "token", "password", "credential")
            ):
                result[str(key)] = "[redacted]"
            elif normalized in {"raw_payload", "payload", "headers", "signed_url"}:
                result[str(key)] = "[omitted]"
            else:
                result[str(key)] = sanitize_customer_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_customer_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if SECRET_VALUE_PATTERN.search(value):
            return "[redacted]"
        if value.startswith(("/", "\\\\")) or re.match(r"^[A-Za-z]:\\", value):
            return Path(value).name
        parsed = urlsplit(value)
        unsafe_url_parts = (
            parsed.query or parsed.fragment or parsed.username or parsed.password
        )
        if parsed.scheme and unsafe_url_parts:
            return f"url_sha256:{_hash(value)}"
    return value


def _finding(
    code: str, severity: str, message: str
) -> CustomerDeploymentReadinessFinding:
    return CustomerDeploymentReadinessFinding(
        code=code, severity=severity, message=message
    )


def _looks_placeholder(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _valid_placeholder_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        return False
    hostname = parsed.hostname.casefold()
    return hostname.endswith(".local") or hostname.endswith(".invalid")


def _has_private_path(value: Any) -> bool:
    if isinstance(value, str):
        return value.startswith(("/", "\\\\")) or bool(re.match(r"^[A-Za-z]:\\", value))
    if isinstance(value, Mapping):
        return any(_has_private_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_private_path(item) for item in value)
    return False


def _has_sensitive_literal(value: Any) -> bool:
    if isinstance(value, str):
        return bool(SECRET_VALUE_PATTERN.search(value))
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold()
            if normalized in {
                "authorization", "secret", "secret_value", "token", "token_value",
                "password", "client_secret", "webhook_secret", "admin_token",
            }:
                return True
            if _has_sensitive_literal(item):
                return True
    if isinstance(value, list):
        return any(_has_sensitive_literal(item) for item in value)
    return False


def _has_signed_url(value: Any) -> bool:
    if isinstance(value, str):
        parsed = urlsplit(value)
        return bool(
            parsed.scheme
            and re.search(r"(?i)(signature|signed|token|expires)=", parsed.query)
        )
    if isinstance(value, Mapping):
        return any(_has_signed_url(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_signed_url(item) for item in value)
    return False


def _validate_ref(name: str, value: str, findings: list) -> None:
    if value and not SAFE_REF_PATTERN.fullmatch(value):
        findings.append(_finding(
            f"{name}_ref", "blocking",
            f"{name.replace('_', ' ').title()} must be an uppercase placeholder reference.",
        ))


def validate_customer_deployment_profile(
    profile: CustomerDeploymentProfile, settings: Settings
) -> list[CustomerDeploymentReadinessFinding]:
    findings: list[CustomerDeploymentReadinessFinding] = []
    dumped = profile.model_dump(mode="json")
    if not settings.customer_deployment_pattern_enabled:
        findings.append(_finding(
            "pattern_disabled", "blocking",
            "Customer deployment pattern generation is disabled.",
        ))
    if len(profile.requested_project_scopes) > settings.customer_profile_max_projects:
        findings.append(_finding(
            "project_cap", "blocking",
            "Requested project count exceeds the configured planning cap.",
        ))
    if (
        settings.customer_profile_require_placeholders
        and not settings.customer_profile_allow_real_ids
        and not _looks_placeholder(profile.customer_label)
    ):
        findings.append(_finding(
            "customer_placeholder", "blocking",
            "Customer label must be clearly fake or a placeholder.",
        ))
    for scope in profile.requested_project_scopes:
        if not settings.customer_profile_allow_real_ids and (
            NUMERIC_ID_PATTERN.fullmatch(scope.company_id)
            or NUMERIC_ID_PATTERN.fullmatch(scope.project_id)
        ):
            findings.append(_finding(
                "real_id", "blocking",
                "Real-looking numeric company or project identifiers are blocked.",
            ))
        if settings.customer_profile_require_placeholders and not all(
            _looks_placeholder(item)
            for item in (scope.company_id, scope.project_id, scope.project_label)
        ):
            findings.append(_finding(
                "project_placeholder", "blocking",
                "Project scope values must be clearly fake placeholders.",
            ))
    if profile.public_base_url and not _valid_placeholder_url(profile.public_base_url):
        findings.append(_finding(
            "public_url", "blocking",
            "Public base URL must use a fake .local or .invalid host with no credentials/query.",
        ))
    if any(host == "*" for host in profile.allowed_hosts):
        findings.append(_finding(
            "wildcard_host", "blocking",
            "Allowed hosts cannot contain a wildcard.",
        ))
    if settings.customer_profile_require_placeholders:
        for host in profile.allowed_hosts:
            if not (host.endswith(".local") or host.endswith(".invalid") or host == "localhost"):
                findings.append(_finding(
                    "host_placeholder", "blocking",
                    "Allowed hosts must use fake .local or .invalid names.",
                ))
    if _has_sensitive_literal(dumped):
        findings.append(_finding(
            "secret_value", "blocking",
            "Profile contains secret, Authorization, signature, or token-like material.",
        ))
    if _has_private_path(dumped):
        findings.append(_finding(
            "private_path", "blocking",
            "Profile contains an absolute private filesystem path.",
        ))
    if _has_signed_url(dumped):
        findings.append(_finding(
            "signed_url", "blocking",
            "Profile contains a raw signed or tokenized URL.",
        ))
    for name, value in (
        ("dmsa_connection", profile.dmsa_connection_ref),
        ("dmsa_client_id", profile.dmsa_client_id_ref),
        ("dmsa_client_secret", profile.dmsa_client_secret_ref),
        ("admin_token", profile.admin_token_ref),
        ("admin_rotation_token", profile.admin_rotation_token_ref),
        ("webhook_secret", profile.webhook_secret_ref),
        ("storage_bucket", profile.storage_bucket_ref),
    ):
        _validate_ref(name, value, findings)

    if profile.environment == "production":
        required_refs = (
            profile.dmsa_connection_ref,
            profile.dmsa_client_id_ref,
            profile.dmsa_client_secret_ref,
            profile.admin_token_ref,
        )
        if not all(required_refs):
            findings.append(_finding(
                "production_refs", "blocking",
                "Production planning requires DMSA and admin secret references.",
            ))
        if not profile.allowed_hosts:
            findings.append(_finding(
                "allowed_hosts", "blocking",
                "Production planning requires explicit allowed hosts.",
            ))
        if (
            profile.admin_auth_plan.mode != "token_required"
            or profile.admin_token_ref == ""
            or profile.admin_rotation_token_ref == ""
        ):
            findings.append(_finding(
                "admin_auth", "blocking",
                "Production planning requires token-required admin primary and rotation refs.",
            ))
        if profile.database_profile.casefold().startswith("sqlite"):
            findings.append(_finding(
                "database", "blocking",
                "SQLite is not accepted as a production database profile.",
            ))
        if profile.secret_provider == "external_placeholder":
            findings.append(_finding(
                "secret_provider", "blocking",
                "The external secret-provider placeholder is not production-ready.",
            ))
        if profile.storage_provider == "external_placeholder":
            findings.append(_finding(
                "storage_provider", "blocking",
                "The external storage placeholder is not production-ready.",
            ))
        if not profile.migration_plan.strip():
            findings.append(_finding(
                "migration_plan", "blocking",
                "Production planning requires an explicit migration plan.",
            ))
        if not profile.backup_plan.strip() or not profile.rollback_plan.strip():
            findings.append(_finding(
                "recovery_plan", "blocking",
                "Production planning requires backup and rollback plans.",
            ))
        if profile.smoke_test_required and not profile.sandbox_smoke_result_ref:
            findings.append(_finding(
                "sandbox_smoke", "blocking",
                "Production planning requires a sanitized sandbox smoke result reference.",
            ))
        if profile.onboarding_packet_required and not profile.onboarding_packet_ref:
            findings.append(_finding(
                "onboarding_packet", "blocking",
                "Production planning requires a GC/Owner onboarding packet reference.",
            ))
        webhook_planned = profile.webhook_plan.enabled
        if webhook_planned and (
            not profile.webhook_secret_ref
            or not profile.webhook_plan.signature_required
        ):
            findings.append(_finding(
                "webhook_signature", "blocking",
                "Planned production webhooks require signatures and a secret reference.",
            ))
        if (
            webhook_planned
            and profile.webhook_verification_required
            and profile.webhook_plan.docs_verification_status != "verified"
        ):
            findings.append(_finding(
                "webhook_verification", "blocking",
                "Planned production webhooks require verified B6 documentation status.",
            ))
    if not findings:
        findings.append(_finding(
            "profile", "info",
            "Profile is valid for local planning; this does not approve or deploy it.",
        ))
    return findings


def build_customer_deployment_readiness_report(
    profile: CustomerDeploymentProfile, settings: Settings
) -> CustomerDeploymentReadinessReport:
    findings = validate_customer_deployment_profile(profile, settings)
    blockers = sum(f.severity == "blocking" for f in findings)
    return CustomerDeploymentReadinessReport(
        profile_name=_safe_profile_name(profile.profile_name),
        environment=profile.environment,
        ready=blockers == 0,
        blocking_findings_count=blockers,
        warning_findings_count=sum(f.severity == "warning" for f in findings),
        findings=findings,
        generated_at=datetime.now(UTC),
    )


def render_customer_launch_checklist(
    profile: CustomerDeploymentProfile, report: CustomerDeploymentReadinessReport
) -> str:
    status = "planning checks passed" if report.ready else "blocked"
    return f"""# Customer launch checklist

Profile: `{_safe_profile_name(profile.profile_name)}`  
Environment: `{profile.environment}`  
Status: **{status}**

- [ ] Resolve every readiness blocker.
- [ ] Confirm GC/Owner project allowlist and requested RFI/Submittal tool scope.
- [ ] Verify secret references through an approved runtime process; never copy values here.
- [ ] Require token-protected admin access for production.
- [ ] Review database migration, verified backup, restore, and rollback plans.
- [ ] Complete the separately gated sandbox smoke plan.
- [ ] Complete B6 documentation verification before any webhook exposure.
- [ ] Complete and approve the GC/Owner onboarding packet.
- [ ] Review explicit allowed hosts, TLS, ingress, monitoring, retention, and emergency stop.
- [ ] Obtain separate approval for infrastructure, deployment, or webhook registration.

This checklist creates no infrastructure and does not approve production.
"""


def render_customer_operations_runbook(
    profile: CustomerDeploymentProfile, report: CustomerDeploymentReadinessReport
) -> str:
    return f"""# Customer operations runbook template

Profile: `{_safe_profile_name(profile.profile_name)}`  
Planning readiness: `{"passed" if report.ready else "blocked"}`

## Routine checks

- Validate the sanitized customer profile and global deployment readiness.
- Confirm admin authentication, secret-reference, storage, migration, and webhook posture.
- Run only approved, manual smoke and verification procedures.

## Emergency stop

- Disable live reads and webhook receiving.
- Remove external ingress through the separately managed deployment platform.
- Pause queue processing and inspect sanitized status only.
- Rotate affected admin, DMSA, and webhook secrets at their external owners.
- Follow reviewed backup/restore and rollback plans.

This template contains no customer contacts, secrets, infrastructure commands, or deployment
automation. Assign real owners and procedures only in a private operational system.
"""


def render_customer_env_template(profile: CustomerDeploymentProfile) -> str:
    return "\n".join([
        "# References/placeholders only. Never put secret values in this generated template.",
        f"PROCORE_INTAKE_ENVIRONMENT={profile.environment}",
        f"PROCORE_INTAKE_ALLOWED_HOSTS={','.join(profile.allowed_hosts)}",
        f"PROCORE_INTAKE_PUBLIC_BASE_URL={profile.public_base_url}",
        f"PROCORE_INTAKE_DMSA_CONNECTION_REF={profile.dmsa_connection_ref}",
        f"PROCORE_INTAKE_DMSA_CLIENT_ID_REF={profile.dmsa_client_id_ref}",
        f"PROCORE_INTAKE_DMSA_CLIENT_SECRET_REF={profile.dmsa_client_secret_ref}",
        f"PROCORE_INTAKE_ADMIN_TOKEN_SECRET_REF={profile.admin_token_ref}",
        f"PROCORE_INTAKE_ADMIN_TOKEN_ROTATION_SECRET_REF={profile.admin_rotation_token_ref}",
        f"PROCORE_INTAKE_WEBHOOK_SECRET_REF={profile.webhook_secret_ref}",
        f"PROCORE_INTAKE_ATTACHMENT_STORAGE_BUCKET_REF={profile.storage_bucket_ref}",
        "",
    ])


def render_customer_secret_inventory(profile: CustomerDeploymentProfile) -> str:
    refs = {
        "dmsa_connection_ref": profile.dmsa_connection_ref,
        "dmsa_client_id_ref": profile.dmsa_client_id_ref,
        "dmsa_client_secret_ref": profile.dmsa_client_secret_ref,
        "admin_token_ref": profile.admin_token_ref,
        "admin_rotation_token_ref": profile.admin_rotation_token_ref,
        "webhook_secret_ref": profile.webhook_secret_ref,
        "storage_bucket_ref": profile.storage_bucket_ref,
    }
    return json.dumps(
        {"references_only": True, "values_included": False, "references": refs},
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_customer_deployment_summary(
    profile: CustomerDeploymentProfile, report: CustomerDeploymentReadinessReport
) -> str:
    findings = "\n".join(
        f"- [{finding.severity}] {finding.code}: {finding.message}"
        for finding in report.findings
    )
    return f"""# Customer deployment planning summary

- Profile: `{_safe_profile_name(profile.profile_name)}`
- Customer label: `{profile.customer_label}`
- Environment: `{profile.environment}`
- Project scopes: {len(profile.requested_project_scopes)}
- Planning readiness: `{"passed" if report.ready else "blocked"}`
- Deployed: `false`
- External calls: `false`

## Findings

{findings}

This local summary is not deployment automation, production approval, or security certification.
"""


def _safe_profile_name(value: str) -> str:
    safe = re.sub(r"[^a-z0-9-]+", "-", value.casefold()).strip("-")
    if not safe or safe in {".", ".."}:
        raise CustomerDeploymentBlockedError("Customer profile name is unsafe.")
    return safe[:80]


def _safe_output_root(output_root: Path) -> Path:
    if ".." in output_root.parts or output_root in {Path("."), Path("/")}:
        raise CustomerDeploymentBlockedError("Customer output path is unsafe.")
    return output_root.resolve()


def write_customer_deployment_artifacts(
    profile: CustomerDeploymentProfile,
    output_root: Path,
    settings: Settings | None = None,
) -> CustomerDeploymentArtifactResult:
    configured = settings or Settings(_env_file=None)
    report = build_customer_deployment_readiness_report(profile, configured)
    if configured.customer_profile_fail_closed and report.blocking_findings_count:
        raise CustomerDeploymentBlockedError(
            "Customer artifact generation blocked by profile readiness findings."
        )
    root = _safe_output_root(output_root)
    directory = root / _safe_profile_name(profile.profile_name)
    if not directory.is_relative_to(root):
        raise CustomerDeploymentBlockedError("Customer artifact path escaped output root.")
    directory.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "deployment-summary.md": render_customer_deployment_summary(profile, report),
        "launch-checklist.md": render_customer_launch_checklist(profile, report),
        "operations-runbook.md": render_customer_operations_runbook(profile, report),
        "env-template.example": render_customer_env_template(profile),
        "secret-inventory.json": render_customer_secret_inventory(profile),
        "readiness-report.json": json.dumps(
            sanitize_customer_value(report.model_dump(mode="json")),
            indent=2,
            sort_keys=True,
        ) + "\n",
    }
    for name, content in artifacts.items():
        if SECRET_VALUE_PATTERN.search(content):
            raise CustomerDeploymentBlockedError(
                "Generated customer artifact failed secret-content safety validation."
            )
        (directory / name).write_text(content)
    return CustomerDeploymentArtifactResult(
        profile_name=_safe_profile_name(profile.profile_name),
        output_directory=directory.relative_to(root).as_posix(),
        files=sorted(artifacts),
    )

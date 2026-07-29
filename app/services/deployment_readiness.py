from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from app.config import Settings
from app.security.admin_access import (
    effective_admin_auth_mode,
    get_admin_auth_config_summary,
    primary_admin_ref,
    rotation_admin_ref,
)
from app.security.secret_provider_factory import (
    build_secret_provider,
    summarize_secret_provider_config,
)
from app.security.secret_refs import SecretRefError, mask_secret_ref, validate_secret_ref
from app.security.secrets import SecretProviderError
from app.services.attachment_storage_factory import (
    build_attachment_storage_provider,
    get_attachment_storage_provider_name,
    summarize_attachment_storage_config,
)
from app.services.attachment_storage_provider import AttachmentStorageProviderError
from app.services.database_readiness import (
    build_database_readiness_report,
)
from app.services.database_readiness import (
    mask_database_url as _mask_database_url,
)
from app.services.storage import build_storage_provider_readiness


class DeploymentFinding(BaseModel):
    check: str
    severity: str
    message: str
    blocks: list[str] = []


class DeploymentReadinessReport(BaseModel):
    environment: str
    ready_for_local: bool
    ready_for_staging: bool
    ready_for_production: bool
    findings: list[DeploymentFinding]
    blocking_findings_count: int
    warning_findings_count: int
    info_findings_count: int
    generated_at: datetime


def _finding(check: str, severity: str, message: str, *blocks: str) -> DeploymentFinding:
    return DeploymentFinding(check=check, severity=severity, message=message, blocks=list(blocks))


def check_environment_profile(settings: Settings) -> list[DeploymentFinding]:
    findings = [_finding("environment", "info", f"Deployment profile is {settings.environment}.")]
    hosts = [item.strip() for item in settings.allowed_hosts.split(",") if item.strip()]
    if not hosts or "*" in hosts:
        findings.append(
            _finding(
                "allowed_hosts",
                "blocking",
                "Production allowed hosts must be explicit and cannot use a wildcard.",
                "production",
            )
        )
    if "*" in [item.strip() for item in settings.cors_origins.split(",")]:
        findings.append(
            _finding(
                "cors_origins",
                "blocking",
                "Production CORS origins cannot use a wildcard.",
                "production",
            )
        )
    return findings


def check_database_url(settings: Settings) -> list[DeploymentFinding]:
    if settings.database_url.lower().startswith("sqlite"):
        return [
            _finding(
                "database",
                "blocking",
                "SQLite is for local development and is not accepted for production.",
                "production",
            )
        ]
    return [_finding("database", "info", "A non-SQLite database URL is configured.")]


def check_live_mode_safety(settings: Settings) -> list[DeploymentFinding]:
    if settings.procore_live_mode_enabled:
        return [
            _finding(
                "live_mode",
                "blocking",
                "Live Procore mode requires a separate approved production review.",
                "production",
            )
        ]
    return [_finding("live_mode", "info", "Live Procore mode is disabled.")]


def check_admin_dashboard_safety(settings: Settings) -> list[DeploymentFinding]:
    mode = effective_admin_auth_mode(settings)
    if mode == "disabled":
        return [
            _finding(
                "admin_dashboard",
                "info",
                "Admin routes are disabled.",
            )
        ]
    findings: list[DeploymentFinding] = []
    if mode == "local_optional":
        findings.append(
            _finding(
                "admin_dashboard",
                "blocking",
                "Local-optional admin access is not accepted in staging or production.",
                "staging",
                "production",
            )
        )
    elif mode == "token_required":
        primary_ref = primary_admin_ref(settings)
        if not primary_ref:
            findings.append(
                _finding(
                    "admin_auth",
                    "blocking",
                    "Token-required admin access needs a primary secret reference.",
                    "staging",
                    "production",
                )
            )
        refs = [ref for ref in (primary_ref, rotation_admin_ref(settings)) if ref]
        for ref in refs:
            try:
                validate_secret_ref(ref, settings)
            except SecretRefError:
                severity = "blocking" if settings.admin_auth_fail_closed else "warning"
                blocks = ("staging", "production") if severity == "blocking" else ()
                findings.append(
                    _finding(
                        "admin_auth",
                        severity,
                        "An admin token reference is invalid.",
                        *blocks,
                    )
                )
        if primary_ref and settings.secret_health_check_enabled:
            try:
                health = build_secret_provider(settings).health_check(refs)
                if health.missing_refs_count:
                    findings.append(
                        _finding(
                            "admin_auth",
                            "blocking",
                            "One or more admin token references are unavailable.",
                            "staging",
                            "production",
                        )
                    )
            except SecretProviderError:
                findings.append(
                    _finding(
                        "admin_auth",
                        "blocking",
                        "The admin token provider is unavailable or misconfigured.",
                        "staging",
                        "production",
                    )
                )
    else:
        findings.append(
            _finding(
                "admin_auth",
                "blocking",
                "Unknown admin authentication mode fails closed.",
                "staging",
                "production",
            )
        )
    if not settings.admin_auth_protect_deployment_routes:
        findings.append(
            _finding(
                "admin_auth",
                "blocking",
                "Sensitive deployment routes are not protected.",
                "staging",
                "production",
            )
        )
    if not findings:
        findings.append(
            _finding(
                "admin_auth",
                "info",
                "Admin and deployment operator routes use token-required access.",
            )
        )
    return findings


def check_webhook_signature_safety(settings: Settings) -> list[DeploymentFinding]:
    if settings.webhooks_enabled and not settings.require_webhook_signature:
        return [
            _finding(
                "webhook_signature",
                "blocking",
                "Enabled production webhooks must require signature verification.",
                "production",
            )
        ]
    if (
        settings.webhooks_enabled
        and settings.require_webhook_signature
        and not settings.webhook_secret_name.strip()
    ):
        return [
            _finding(
                "webhook_signature",
                "blocking",
                "Webhook signatures require a secret reference.",
                "production",
            )
        ]
    return [_finding("webhook_signature", "info", "Webhook signature posture is safe.")]


def check_webhook_verification_safety(settings: Settings) -> list[DeploymentFinding]:
    if not settings.webhooks_enabled:
        return [_finding(
            "webhook_verification", "info",
            "Webhook receiver is disabled; a production verification record is not required.",
        )]
    if settings.webhook_verification_docs_status in {"unverified", "deprecated"}:
        return [_finding(
            "webhook_verification", "blocking",
            "Enabled production webhooks require current manually verified "
            "documentation assumptions.",
            "production",
        )]
    if settings.webhook_verification_docs_status == "needs_review":
        return [_finding(
            "webhook_verification", "warning",
            "Webhook documentation assumptions still need operator review.",
            "production",
        )]
    return [_finding(
        "webhook_verification", "info",
        "Webhook documentation assumptions are marked manually verified.",
    )]


def check_customer_deployment_pattern(settings: Settings) -> list[DeploymentFinding]:
    findings = []
    if settings.customer_deployment_pattern_enabled:
        findings.append(_finding(
            "customer_deployment_pattern", "info",
            "Local customer deployment profile validation is available; it deploys nothing.",
        ))
    else:
        findings.append(_finding(
            "customer_deployment_pattern", "warning",
            "Customer deployment profile validation is disabled.",
        ))
    if settings.customer_profile_allow_real_ids:
        findings.append(_finding(
            "customer_profile_ids", "warning",
            "Customer profile validation permits real-looking IDs; public examples must not.",
        ))
    else:
        findings.append(_finding(
            "customer_profile_ids", "info",
            "Real-looking customer and project identifiers are blocked by default.",
        ))
    output = settings.customer_profile_output_root
    if output in {Path("."), Path("/")} or ".." in output.parts:
        findings.append(_finding(
            "customer_profile_output", "blocking",
            "Customer profile output root is unsafe.",
            "local", "staging", "production",
        ))
    else:
        findings.append(_finding(
            "customer_profile_output", "info",
            "Customer planning output uses a dedicated ignored directory.",
        ))
    return findings


def check_pilot_readiness_pattern(settings: Settings) -> list[DeploymentFinding]:
    findings = [
        _finding(
            "pilot_readiness",
            "info" if settings.pilot_readiness_enabled else "warning",
            "Local pilot readiness CLI gate is available."
            if settings.pilot_readiness_enabled
            else "Local pilot readiness validation is disabled.",
        )
    ]
    findings.append(_finding(
        "pilot_production",
        "warning" if settings.pilot_readiness_allow_production else "info",
        "Production pilot profiles are explicitly allowed."
        if settings.pilot_readiness_allow_production
        else "Production pilot profiles are blocked by default.",
    ))
    findings.append(_finding(
        "pilot_real_ids",
        "warning" if settings.pilot_readiness_allow_real_ids else "info",
        "Real-looking IDs are allowed by pilot profile settings."
        if settings.pilot_readiness_allow_real_ids
        else "Real-looking pilot identifiers are blocked by default.",
    ))
    output = settings.pilot_readiness_output_root
    if output in {Path("."), Path("/")} or ".." in output.parts:
        findings.append(_finding(
            "pilot_output", "blocking",
            "Pilot readiness output root is unsafe.",
            "local", "staging", "production",
        ))
    else:
        findings.append(_finding(
            "pilot_output", "info",
            "Pilot readiness output uses a dedicated ignored directory.",
        ))
    return findings


def check_private_workspace_bootstrap(settings: Settings) -> list[DeploymentFinding]:
    output = settings.private_workspace_root
    output_safe = output not in {Path("."), Path("/")} and ".." not in output.parts
    validators = Path("scripts/init_private_workspace.py").is_file() and Path(
        "scripts/validate_private_workspace.py"
    ).is_file()
    posture = (
        settings.private_workspace_enabled
        and output_safe
        and not settings.private_workspace_allow_real_ids
        and not settings.private_workspace_allow_real_identities
        and not settings.private_workspace_allow_file_contents
        and not settings.private_workspace_allow_absolute_paths
        and validators
    )
    return [
        _finding(
            "private_workspace_bootstrap",
            "info" if posture else "warning",
            "Private workspace bootstrap has a safe placeholder-only local posture."
            if posture
            else "Private workspace bootstrap posture needs review.",
        )
    ]


def check_private_evidence_pattern(settings: Settings) -> list[DeploymentFinding]:
    findings = [
        _finding(
            "private_evidence_pattern",
            "info" if settings.private_evidence_pattern_enabled else "warning",
            "Local private-evidence template and validation CLIs are available."
            if settings.private_evidence_pattern_enabled
            else "Private-evidence workspace pattern is disabled.",
        ),
        _finding(
            "private_evidence_ids",
            "warning" if settings.private_evidence_allow_real_ids else "info",
            "Real-looking identifiers are allowed by private-evidence settings."
            if settings.private_evidence_allow_real_ids
            else "Real-looking identifiers are blocked by default.",
        ),
        _finding(
            "private_evidence_contents",
            "warning" if settings.private_evidence_allow_file_contents else "info",
            "Evidence file contents are allowed by private-evidence settings."
            if settings.private_evidence_allow_file_contents
            else "Evidence file contents are blocked by default.",
        ),
    ]
    output = settings.private_evidence_output_root
    if output in {Path("."), Path("/")} or ".." in output.parts:
        findings.append(
            _finding(
                "private_evidence_output",
                "blocking",
                "Private-evidence output root is unsafe.",
                "local",
                "staging",
                "production",
            )
        )
    else:
        findings.append(
            _finding(
                "private_evidence_output",
                "info",
                "Private-evidence output uses a dedicated ignored directory.",
            )
        )
    return findings


def check_evidence_review_pattern(settings: Settings) -> list[DeploymentFinding]:
    findings = [
        _finding(
            "evidence_review_pattern",
            "info" if settings.evidence_review_enabled else "warning",
            "Local evidence review and expiry CLIs are available."
            if settings.evidence_review_enabled
            else "Evidence review and expiry workflow is disabled.",
        ),
        _finding(
            "evidence_review_identities",
            "warning" if settings.evidence_review_allow_real_identities else "info",
            "Real reviewer identities are allowed by review settings."
            if settings.evidence_review_allow_real_identities
            else "Real reviewer identities are blocked by default.",
        ),
        _finding(
            "evidence_review_ids",
            "warning" if settings.evidence_review_allow_real_ids else "info",
            "Real-looking identifiers are allowed by review settings."
            if settings.evidence_review_allow_real_ids
            else "Real-looking review identifiers are blocked by default.",
        ),
        _finding(
            "evidence_review_contents",
            "warning" if settings.evidence_review_allow_file_contents else "info",
            "Evidence contents are allowed by review settings."
            if settings.evidence_review_allow_file_contents
            else "Evidence contents are blocked by default.",
        ),
        _finding(
            "evidence_review_expiry",
            "info",
            "Evidence review uses bounded local expiry and warning windows.",
        ),
    ]
    output = settings.evidence_review_output_root
    if output in {Path("."), Path("/")} or ".." in output.parts:
        findings.append(
            _finding(
                "evidence_review_output",
                "blocking",
                "Evidence review output root is unsafe.",
                "local",
                "staging",
                "production",
            )
        )
    else:
        findings.append(
            _finding(
                "evidence_review_output",
                "info",
                "Evidence review output uses a dedicated ignored directory.",
            )
        )
    return findings


def check_pilot_approval_packet_pattern(settings: Settings) -> list[DeploymentFinding]:
    findings = [
        _finding(
            "pilot_approval_packet",
            "info" if settings.pilot_approval_packet_enabled else "warning",
            "Local placeholder pilot approval packet CLIs are available."
            if settings.pilot_approval_packet_enabled
            else "Pilot approval packet pattern is disabled.",
        ),
        _finding(
            "pilot_approval_identities",
            "warning" if settings.pilot_approval_packet_allow_real_identities else "info",
            "Real approval identities are allowed by packet settings."
            if settings.pilot_approval_packet_allow_real_identities
            else "Real approval identities are blocked by default.",
        ),
        _finding(
            "pilot_approval_ids",
            "warning" if settings.pilot_approval_packet_allow_real_ids else "info",
            "Real-looking identifiers are allowed by packet settings."
            if settings.pilot_approval_packet_allow_real_ids
            else "Real-looking approval identifiers are blocked by default.",
        ),
        _finding(
            "pilot_approval_contents",
            "warning" if settings.pilot_approval_packet_allow_file_contents else "info",
            "Private file contents are allowed by packet settings."
            if settings.pilot_approval_packet_allow_file_contents
            else "Private file contents are blocked by default.",
        ),
        _finding(
            "pilot_approval_production",
            "warning" if settings.pilot_approval_packet_allow_production else "info",
            "Production approval packets are allowed by packet settings."
            if settings.pilot_approval_packet_allow_production
            else "Production approval packets are blocked by default.",
        ),
    ]
    output = settings.pilot_approval_packet_output_root
    if output in {Path("."), Path("/")} or ".." in output.parts:
        findings.append(
            _finding(
                "pilot_approval_output",
                "blocking",
                "Pilot approval output root is unsafe.",
                "local",
                "staging",
                "production",
            )
        )
    else:
        findings.append(
            _finding(
                "pilot_approval_output",
                "info",
                "Pilot approval output uses a dedicated ignored directory.",
            )
        )
    return findings


def check_attachment_storage_safety(settings: Settings) -> list[DeploymentFinding]:
    findings: list[DeploymentFinding] = []
    name = get_attachment_storage_provider_name(settings)
    if settings.attachment_storage_max_object_bytes <= 0:
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "Attachment object-size limit must be positive.",
                "staging",
                "production",
            )
        )
    if not settings.attachment_storage_require_safe_keys:
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "Safe attachment object keys are required.",
                "staging",
                "production",
            )
        )
    if name == "local":
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "Local attachment storage is not accepted as the final production backend.",
                "production",
            )
        )
    elif name == "test":
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "The in-memory test storage provider is forbidden outside tests.",
                "staging",
                "production",
            )
        )
    elif name == "disabled":
        findings.append(
            _finding(
                "attachment_storage", "blocking", "Attachment storage is disabled.", "production"
            )
        )
    elif name == "external_placeholder":
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "External attachment storage is a fail-closed placeholder and is not implemented.",
                "staging",
                "production",
            )
        )
    else:
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "Unknown attachment storage provider fails closed.",
                "staging",
                "production",
            )
        )
    if not settings.attachment_fixture_downloads_only:
        findings.append(
            _finding(
                "attachment_storage",
                "blocking",
                "Non-fixture downloads have no implemented production storage provider.",
                "production",
            )
        )
    else:
        findings.append(_finding("attachment_storage", "info", "Downloads remain fixture-only."))
    if not settings.attachment_storage_health_check_enabled:
        findings.append(
            _finding(
                "attachment_storage_health",
                "warning",
                "Attachment storage health checks are disabled.",
            )
        )
    else:
        try:
            health = build_attachment_storage_provider(settings).health_check()
            if health.available:
                findings.append(
                    _finding(
                        "attachment_storage_health",
                        "info",
                        "Attachment storage health check completed without external calls.",
                    )
                )
            else:
                findings.append(
                    _finding(
                        "attachment_storage_health",
                        "blocking",
                        "Attachment storage provider is unavailable.",
                        "production",
                    )
                )
        except (AttachmentStorageProviderError, ValueError):
            findings.append(
                _finding(
                    "attachment_storage_health",
                    "blocking",
                    "Attachment storage provider is unavailable or misconfigured.",
                    "staging",
                    "production",
                )
            )
    return findings


def check_storage_provider_posture(settings: Settings) -> list[DeploymentFinding]:
    readiness = build_storage_provider_readiness(settings)
    return [
        _finding(
            "storage_provider_posture",
            "info" if readiness.ready else "warning",
            "D2 storage provider is locally available with sanitized diagnostics."
            if readiness.ready
            else "D2 storage provider is unavailable or needs private configuration.",
        )
    ]


def check_database_provider_posture(settings: Settings) -> list[DeploymentFinding]:
    mode = "pilot" if settings.environment in {"staging", "production"} else "demo"
    report = build_database_readiness_report(settings, mode)
    return [
        _finding(
            "database_provider_posture",
            item.severity,
            item.message,
            *(("staging", "production") if item.severity == "blocking" else ()),
        )
        for item in report.findings
    ]


def check_secret_provider_safety(settings: Settings) -> list[DeploymentFinding]:
    findings: list[DeploymentFinding] = []
    if settings.secret_provider == "env":
        findings.append(
            _finding(
                "secret_provider",
                "blocking",
                "The environment provider requires externally injected runtime secrets and "
                "is not accepted as the final production secret-manager adapter.",
                "production",
            )
        )
    elif settings.secret_provider == "file":
        findings.append(
            _finding(
                "secret_provider",
                "blocking",
                "The file provider supports local private use but requires separate "
                "production secret-management review.",
                "production",
            )
        )
    elif settings.secret_provider == "disabled":
        findings.append(
            _finding(
                "secret_provider",
                "blocking",
                "The disabled secret provider fails closed and cannot support production.",
                "production",
            )
        )
    elif settings.secret_provider == "external_placeholder":
        findings.append(
            _finding(
                "secret_provider",
                "blocking",
                "The external placeholder performs no secret-manager integration.",
                "production",
            )
        )
    elif settings.secret_provider == "test":
        findings.append(
            _finding(
                "secret_provider",
                "blocking",
                "The in-memory test provider is forbidden in production.",
                "production",
            )
        )
    required_refs = []
    if settings.admin_require_token and settings.admin_token_secret_name:
        required_refs.append(settings.admin_token_secret_name)
    if settings.require_webhook_signature and settings.webhook_secret_name:
        required_refs.append(settings.webhook_secret_name)
    for ref in required_refs:
        try:
            if settings.secret_provider == "file":
                build_secret_provider(settings).describe_ref(ref)
            else:
                validate_secret_ref(ref, settings)
        except SecretRefError:
            findings.append(
                _finding(
                    "secret_reference",
                    "blocking",
                    "A required secret reference is invalid or missing its prefix.",
                    "production",
                )
            )
    if not settings.secret_health_check_enabled:
        findings.append(
            _finding(
                "secret_provider_health",
                "warning",
                "Secret-provider health checks are disabled.",
            )
        )
    else:
        try:
            provider = build_secret_provider(settings)
            health = provider.health_check(required_refs)
            if health.missing_refs_count:
                findings.append(
                    _finding(
                        "secret_provider_health",
                        "blocking",
                        "One or more required secret references are missing.",
                        "production",
                    )
                )
            else:
                findings.append(
                    _finding(
                        "secret_provider_health",
                        "info",
                        "Provider health check completed without exposing values.",
                    )
                )
        except SecretProviderError:
            findings.append(
                _finding(
                    "secret_provider_health",
                    "blocking",
                    "The selected secret provider is unavailable or misconfigured.",
                    "production",
                )
            )
    return findings


def check_output_paths(settings: Settings) -> list[DeploymentFinding]:
    root = Path.cwd().resolve()
    findings: list[DeploymentFinding] = []
    for name, configured in (
        ("attachment_storage_root", settings.attachment_storage_root),
        ("packet_output_root", settings.packet_output_root),
    ):
        path = configured if configured.is_absolute() else root / configured
        if path.resolve().is_relative_to(root):
            findings.append(
                _finding(
                    name,
                    "blocking",
                    f"{name} is inside the repository; production output must be external.",
                    "production",
                )
            )
    return findings or [_finding("output_paths", "info", "Output paths are external.")]


def check_migration_safety(settings: Settings) -> list[DeploymentFinding]:
    from app.services.migration_status import build_migration_status_report

    findings: list[DeploymentFinding] = []
    if settings.auto_run_migrations:
        findings.append(
            _finding(
                "migrations",
                "blocking",
                "Automatic startup migrations are not allowed by the B3 safety model.",
                "production",
            )
        )
    if settings.migration_allow_destructive:
        findings.append(
            _finding(
                "migrations",
                "blocking",
                "Destructive migrations require separate operator review and are disabled.",
                "production",
            )
        )
    status = build_migration_status_report(settings)
    if any(item.severity == "error" for item in status.findings):
        severity = (
            "blocking"
            if settings.environment == "production"
            and settings.fail_readiness_on_pending_migrations
            else "warning"
        )
        blocks = ("production",) if severity == "blocking" else ()
        findings.append(
            _finding(
                "migrations",
                severity,
                "Migration status could not be inspected safely.",
                *blocks,
            )
        )
    elif status.pending_migration_detected:
        severity = (
            "blocking"
            if settings.environment == "production"
            and settings.fail_readiness_on_pending_migrations
            else "warning"
        )
        blocks = ("production",) if severity == "blocking" else ()
        findings.append(
            _finding(
                "migrations",
                severity,
                "Pending database migrations were detected; no migration was run.",
                *blocks,
            )
        )
    else:
        findings.append(
            _finding(
                "migrations",
                "info",
                "Migration status is at head or checks are explicitly disabled.",
            )
        )
    return findings


def build_deployment_readiness_report(settings: Settings) -> DeploymentReadinessReport:
    findings: list[DeploymentFinding] = []
    for check in (
        check_environment_profile,
        check_database_url,
        check_live_mode_safety,
        check_admin_dashboard_safety,
        check_webhook_signature_safety,
        check_webhook_verification_safety,
        check_customer_deployment_pattern,
        check_pilot_readiness_pattern,
        check_private_workspace_bootstrap,
        check_private_evidence_pattern,
        check_evidence_review_pattern,
        check_pilot_approval_packet_pattern,
        check_attachment_storage_safety,
        check_storage_provider_posture,
        check_database_provider_posture,
        check_secret_provider_safety,
        check_output_paths,
        check_migration_safety,
    ):
        findings.extend(check(settings))
    production_blockers = sum(
        finding.severity == "blocking" and "production" in finding.blocks for finding in findings
    )
    staging_blockers = sum(
        finding.severity == "blocking" and "staging" in finding.blocks for finding in findings
    )
    return DeploymentReadinessReport(
        environment=settings.environment,
        ready_for_local=True,
        ready_for_staging=staging_blockers == 0,
        ready_for_production=production_blockers == 0,
        findings=findings,
        blocking_findings_count=production_blockers,
        warning_findings_count=sum(f.severity == "warning" for f in findings),
        info_findings_count=sum(f.severity == "info" for f in findings),
        generated_at=datetime.now(UTC),
    )


def mask_database_url(database_url: str) -> str:
    return _mask_database_url(database_url)


def build_sanitized_config_summary(settings: Settings) -> dict:
    masked_refs = []
    for ref in (settings.admin_token_secret_name, settings.webhook_secret_name):
        if ref:
            masked_refs.append(mask_secret_ref(ref, settings))
    return {
        "environment": settings.environment,
        "database_url": mask_database_url(settings.database_url),
        "procore_mode": settings.procore_mode,
        "live_mode_enabled": settings.procore_live_mode_enabled,
        "public_base_url_configured": bool(settings.public_base_url),
        "allowed_hosts": [
            item.strip() for item in settings.allowed_hosts.split(",") if item.strip()
        ],
        "cors_origins_configured": bool(settings.cors_origins.strip()),
        "log_level": settings.log_level,
        "startup_checks_enabled": settings.enable_startup_checks,
        "admin_dashboard_enabled": settings.admin_dashboard_enabled,
        "admin_token_required": settings.admin_require_token,
        "admin_token_reference_configured": bool(settings.admin_token_secret_name.strip()),
        "admin_auth": get_admin_auth_config_summary(settings).model_dump(),
        "webhooks_enabled": settings.webhooks_enabled,
        "webhook_signature_required": settings.require_webhook_signature,
        "webhook_secret_reference_configured": bool(settings.webhook_secret_name.strip()),
        "webhook_verification": {
            "enabled": settings.webhook_verification_enabled,
            "docs_status": settings.webhook_verification_docs_status,
            "docs_check_required": settings.webhook_verification_require_docs_check,
            "production_allowed": settings.webhook_verification_allow_production,
            "synthetic_only": True,
        },
        "customer_deployment_pattern": {
            "enabled": settings.customer_deployment_pattern_enabled,
            "placeholders_required": settings.customer_profile_require_placeholders,
            "real_ids_allowed": settings.customer_profile_allow_real_ids,
            "max_projects": settings.customer_profile_max_projects,
            "fail_closed": settings.customer_profile_fail_closed,
            "deployment_automation": False,
        },
        "pilot_readiness": {
            "enabled": settings.pilot_readiness_enabled,
            "production_allowed": settings.pilot_readiness_allow_production,
            "real_ids_allowed": settings.pilot_readiness_allow_real_ids,
            "placeholders_required": settings.pilot_readiness_require_placeholders,
            "fail_closed": settings.pilot_readiness_fail_closed,
            "deployment_automation": False,
        },
        "private_workspace": {
            "enabled": settings.private_workspace_enabled,
            "output_root_safe": (
                settings.private_workspace_root not in {Path("."), Path("/")}
                and ".." not in settings.private_workspace_root.parts
            ),
            "real_ids_allowed": settings.private_workspace_allow_real_ids,
            "real_identities_allowed": settings.private_workspace_allow_real_identities,
            "file_contents_allowed": settings.private_workspace_allow_file_contents,
            "absolute_paths_allowed": settings.private_workspace_allow_absolute_paths,
            "validators_available": Path("scripts/validate_private_workspace.py").is_file(),
            "generated_workspace_ignored": True,
        },
        "private_evidence": {
            "enabled": settings.private_evidence_pattern_enabled,
            "placeholders_required": settings.private_evidence_require_placeholders,
            "real_ids_allowed": settings.private_evidence_allow_real_ids,
            "file_contents_allowed": settings.private_evidence_allow_file_contents,
            "absolute_paths_allowed": settings.private_evidence_allow_absolute_paths,
            "max_items": settings.private_evidence_max_items,
            "fail_closed": settings.private_evidence_fail_closed,
            "output_root_safe": (
                settings.private_evidence_output_root not in {Path("."), Path("/")}
                and ".." not in settings.private_evidence_output_root.parts
            ),
            "validators_available": True,
            "generated_artifacts_allowed_in_repo": False,
        },
        "evidence_review": {
            "enabled": settings.evidence_review_enabled,
            "placeholders_required": settings.evidence_review_require_placeholders,
            "real_identities_allowed": settings.evidence_review_allow_real_identities,
            "real_ids_allowed": settings.evidence_review_allow_real_ids,
            "file_contents_allowed": settings.evidence_review_allow_file_contents,
            "absolute_paths_allowed": settings.evidence_review_allow_absolute_paths,
            "default_expiry_days": settings.evidence_review_default_expiry_days,
            "max_expiry_days": settings.evidence_review_max_expiry_days,
            "warn_within_days": settings.evidence_review_warn_within_days,
            "max_items": settings.evidence_review_max_items,
            "fail_closed": settings.evidence_review_fail_closed,
            "output_root_safe": (
                settings.evidence_review_output_root not in {Path("."), Path("/")}
                and ".." not in settings.evidence_review_output_root.parts
            ),
            "validators_available": True,
            "generated_artifacts_allowed_in_repo": False,
            "notifications_enabled": False,
        },
        "pilot_approval_packet": {
            "enabled": settings.pilot_approval_packet_enabled,
            "placeholders_required": settings.pilot_approval_packet_require_placeholders,
            "real_identities_allowed": settings.pilot_approval_packet_allow_real_identities,
            "real_ids_allowed": settings.pilot_approval_packet_allow_real_ids,
            "file_contents_allowed": settings.pilot_approval_packet_allow_file_contents,
            "absolute_paths_allowed": settings.pilot_approval_packet_allow_absolute_paths,
            "production_allowed": settings.pilot_approval_packet_allow_production,
            "max_approvers": settings.pilot_approval_packet_max_approvers,
            "max_conditions": settings.pilot_approval_packet_max_conditions,
            "fail_closed": settings.pilot_approval_packet_fail_closed,
            "output_root_safe": (
                settings.pilot_approval_packet_output_root not in {Path("."), Path("/")}
                and ".." not in settings.pilot_approval_packet_output_root.parts
            ),
            "validators_available": True,
            "generated_artifacts_allowed_in_repo": False,
            "approval_or_deployment_automation": False,
        },
        "attachment_fixture_downloads_only": settings.attachment_fixture_downloads_only,
        "attachment_storage": summarize_attachment_storage_config(settings),
        "secret_provider": summarize_secret_provider_config(settings),
        "masked_required_secret_refs": masked_refs,
    }

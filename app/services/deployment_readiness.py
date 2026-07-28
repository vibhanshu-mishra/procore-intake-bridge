from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel

from app.config import Settings
from app.security.secret_provider_factory import (
    build_secret_provider,
    summarize_secret_provider_config,
)
from app.security.secret_refs import SecretRefError, mask_secret_ref, validate_secret_ref
from app.security.secrets import SecretProviderError


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
    return DeploymentFinding(
        check=check, severity=severity, message=message, blocks=list(blocks)
    )


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
    if settings.admin_dashboard_enabled and (
        not settings.admin_require_token or not settings.admin_token_secret_name.strip()
    ):
        return [
            _finding(
                "admin_dashboard",
                "blocking",
                "The production admin dashboard requires a configured token reference.",
                "production",
            )
        ]
    return [_finding("admin_dashboard", "info", "Admin dashboard access is constrained.")]


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


def check_attachment_storage_safety(settings: Settings) -> list[DeploymentFinding]:
    if not settings.attachment_fixture_downloads_only:
        return [
            _finding(
                "attachment_storage",
                "blocking",
                "Non-fixture downloads have no approved production storage backend.",
                "production",
            )
        ]
    return [_finding("attachment_storage", "info", "Downloads remain fixture-only.")]


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
        check_attachment_storage_safety,
        check_secret_provider_safety,
        check_output_paths,
        check_migration_safety,
    ):
        findings.extend(check(settings))
    production_blockers = sum(
        finding.severity == "blocking" and "production" in finding.blocks
        for finding in findings
    )
    staging_blockers = sum(
        finding.severity == "blocking" and "staging" in finding.blocks
        for finding in findings
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
    try:
        parsed = urlsplit(database_url)
        if parsed.password is None:
            return database_url
        hostname = parsed.hostname or ""
        if parsed.port:
            hostname = f"{hostname}:{parsed.port}"
        username = parsed.username or ""
        netloc = f"{username}:***@{hostname}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except ValueError:
        return "[invalid database URL]"


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
        "webhooks_enabled": settings.webhooks_enabled,
        "webhook_signature_required": settings.require_webhook_signature,
        "webhook_secret_reference_configured": bool(settings.webhook_secret_name.strip()),
        "attachment_fixture_downloads_only": settings.attachment_fixture_downloads_only,
        "secret_provider": summarize_secret_provider_config(settings),
        "masked_required_secret_refs": masked_refs,
    }

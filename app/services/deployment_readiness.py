from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel

from app.config import Settings


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
    if settings.secret_provider == "env":
        return [
            _finding(
                "secret_provider",
                "warning",
                "Environment secrets are suitable only with external runtime injection for "
                "small or self-hosted deployments.",
            )
        ]
    return [_finding("secret_provider", "info", "A non-environment secret provider is configured.")]


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
        "secret_provider": settings.secret_provider,
    }

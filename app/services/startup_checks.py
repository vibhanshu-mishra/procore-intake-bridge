import logging

from app.config import Settings
from app.services.deployment_readiness import (
    DeploymentReadinessReport,
    build_deployment_readiness_report,
)

logger = logging.getLogger(__name__)


class StartupCheckError(RuntimeError):
    """Raised when a production deployment fails closed without exposing secrets."""


def run_startup_checks(settings: Settings) -> DeploymentReadinessReport:
    report = build_deployment_readiness_report(settings)
    if not settings.enable_startup_checks:
        logger.warning("Startup safety checks are disabled.")
        return report
    if (
        settings.environment == "production"
        and settings.require_safe_production_settings
        and settings.fail_startup_on_unsafe_production
        and report.blocking_findings_count
    ):
        raise StartupCheckError(
            f"Unsafe production settings: {report.blocking_findings_count} "
            "blocking deployment finding(s). Run the sanitized readiness report."
        )
    return report

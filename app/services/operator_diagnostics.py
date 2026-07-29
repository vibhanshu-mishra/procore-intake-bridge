from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.models.onboarding_packets import OnboardingPacket
from app.models.sync_profiles import SyncProfile
from app.models.sync_runs import SyncRun
from app.models.webhook_events import WebhookEvent
from app.schemas.operator_diagnostics import (
    ConfigurationDiagnosticSummary,
    DatabaseDiagnosticSummary,
    DependencyDiagnosticSummary,
    DiagnosticFinding,
    DiagnosticSection,
    DiagnosticSeverity,
    OperatorDiagnosticsReport,
    QueueDiagnosticSummary,
    RedactionDiagnosticSummary,
    RouteDiagnosticSummary,
    RuntimeDiagnosticSummary,
    SafetyDiagnosticSummary,
)
from app.security.admin_access import effective_admin_auth_mode
from app.services.attachment_storage_factory import (
    get_attachment_storage_provider_name,
)
from app.services.deployment_readiness import build_deployment_readiness_report
from app.services.diagnostic_redaction import (
    DiagnosticRedactionError,
    assert_diagnostics_safe,
    redact_diagnostic_value,
    summarize_redaction,
)
from app.services.migration_status import build_migration_status_report

APP_VERSION = "0.1.0"


class OperatorDiagnosticsError(RuntimeError):
    """A sanitized operator diagnostics operation failed."""


class OperatorDiagnosticsBlockedError(OperatorDiagnosticsError):
    """Diagnostics are disabled or failed strict safety validation."""


def collect_runtime_summary(settings: Settings) -> RuntimeDiagnosticSummary:
    return RuntimeDiagnosticSummary(
        environment=settings.environment,
        app_version=APP_VERSION,
        diagnostics_enabled=settings.operator_diagnostics_enabled,
    )


def collect_dependency_summary(settings: Settings) -> DependencyDiagnosticSummary:
    if not settings.operator_diagnostics_include_dependency_inventory:
        return DependencyDiagnosticSummary(available=False)
    packages = {}
    for package in ("alembic", "fastapi", "pydantic", "sqlalchemy", "uvicorn"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "unavailable"
    return DependencyDiagnosticSummary(available=True, packages=packages)


def collect_route_inventory(app: FastAPI | None) -> RouteDiagnosticSummary:
    if app is None:
        return RouteDiagnosticSummary(available=False)
    routes = []
    method_counts: dict[str, int] = {}
    candidates = []
    for candidate in app.routes:
        if isinstance(candidate, APIRoute):
            candidates.append(candidate)
        elif original_router := getattr(candidate, "original_router", None):
            candidates.extend(
                route for route in original_router.routes if isinstance(route, APIRoute)
            )
    for route in candidates:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
        for method in methods:
            method_counts[method] = method_counts.get(method, 0) + 1
        routes.append(
            {
                "path": route.path,
                "methods": methods,
                "name": route.name,
                "read_only": all(method == "GET" for method in methods),
                "operator": route.path.startswith("/deployment"),
                "admin": route.path.startswith("/admin"),
            }
        )
    return RouteDiagnosticSummary(
        available=True,
        total=len(routes),
        method_counts=method_counts,
        routes=routes,
    )


def _count(session: Session, model: Any) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def collect_database_summary(
    db_session: Session | None,
) -> DatabaseDiagnosticSummary:
    if db_session is None:
        return DatabaseDiagnosticSummary(available=False)
    return DatabaseDiagnosticSummary(
        available=True,
        table_counts={
            "sync_profiles": _count(db_session, SyncProfile),
            "sync_runs": _count(db_session, SyncRun),
            "intake_records": _count(db_session, IntakeRecord),
            "attachment_manifests": _count(db_session, AttachmentObject),
            "webhook_events": _count(db_session, WebhookEvent),
            "onboarding_packets": _count(db_session, OnboardingPacket),
        },
    )


def collect_queue_summary(db_session: Session | None) -> QueueDiagnosticSummary:
    if db_session is None:
        return QueueDiagnosticSummary(available=False)
    counts = dict(
        db_session.execute(
            select(WebhookEvent.processing_status, func.count()).group_by(
                WebhookEvent.processing_status
            )
        ).all()
    )
    return QueueDiagnosticSummary(
        available=True,
        pending=int(counts.get("queued", 0)),
        failed=int(counts.get("failed", 0)),
        done=int(counts.get("completed", 0) + counts.get("processed", 0)),
        skipped=int(counts.get("skipped", 0)),
    )


def collect_configuration_summary(
    settings: Settings,
) -> ConfigurationDiagnosticSummary:
    if not settings.operator_diagnostics_include_config_summary:
        return ConfigurationDiagnosticSummary(available=False)
    return ConfigurationDiagnosticSummary(
        available=True,
        posture={
            "admin_auth_mode": effective_admin_auth_mode(settings),
            "admin_auth_enforced": effective_admin_auth_mode(settings) == "token_required",
            "deployment_routes_protected": settings.admin_auth_protect_deployment_routes,
            "secret_provider_kind": settings.secret_provider,
            "secret_provider_health_checks": settings.secret_health_check_enabled,
            "attachment_storage_provider": get_attachment_storage_provider_name(settings),
            "storage_provider": settings.storage_provider,
            "storage_provider_fail_closed": settings.storage_provider_fail_closed,
            "database_provider": settings.database_provider,
            "database_external_connect_enabled": (settings.database_external_connect_enabled),
            "database_url_reference_configured": bool(settings.database_url_ref.strip()),
            "deployment_target": settings.deployment_target,
            "deployment_recipes_enabled": settings.deployment_recipes_enabled,
            "deployment_external_provisioning_enabled": (
                settings.deployment_external_provisioning_enabled
            ),
            "attachment_fixture_only": settings.attachment_fixture_downloads_only,
            "migration_check_enabled": settings.migration_check_enabled,
            "sandbox_smoke_enabled": settings.sandbox_smoke_enabled,
            "webhook_receiver_enabled": settings.webhooks_enabled,
            "webhook_signing_enforced": settings.require_webhook_signature,
            "webhook_docs_status": settings.webhook_verification_docs_status,
            "customer_pattern_enabled": settings.customer_deployment_pattern_enabled,
            "customer_real_ids_allowed": settings.customer_profile_allow_real_ids,
            "environment_key_names_included": settings.operator_diagnostics_include_env_key_names,
        },
    )


def collect_safety_summary(settings: Settings) -> SafetyDiagnosticSummary:
    return SafetyDiagnosticSummary(
        raw_logs_included=settings.support_bundle_include_raw_logs,
        database_file_included=settings.support_bundle_include_db_file,
        attachments_included=settings.support_bundle_include_attachments,
        payloads_included=settings.support_bundle_include_payloads,
    )


def collect_existing_readiness_summaries(
    settings: Settings, db_session: Session | None = None
) -> list[DiagnosticSection]:
    del db_session
    local_database = settings.database_url.casefold().startswith("sqlite")
    sections = []
    if local_database:
        deployment = build_deployment_readiness_report(settings)
        sections.append(
            DiagnosticSection(
                name="deployment_readiness",
                status="ready" if deployment.ready_for_production else "blocked",
                summary={
                    "production_ready": deployment.ready_for_production,
                    "blocking_count": deployment.blocking_findings_count,
                    "warning_count": deployment.warning_findings_count,
                    "external_connection": False,
                },
            )
        )
    else:
        sections.append(
            DiagnosticSection(
                name="deployment_readiness",
                status="unavailable",
                summary={"external_connection": False},
            )
        )
    if local_database:
        migration = build_migration_status_report(settings)
        sections.append(
            DiagnosticSection(
                name="migration_status",
                status="ready" if migration.is_at_head else "attention",
                summary={
                    "check_enabled": migration.migration_check_enabled,
                    "at_head": migration.is_at_head,
                    "pending_count": migration.pending_migrations_count,
                    "external_connection": False,
                },
            )
        )
    else:
        sections.append(
            DiagnosticSection(
                name="migration_status",
                status="unavailable",
                summary={
                    "check_enabled": settings.migration_check_enabled,
                    "external_connection": False,
                },
            )
        )
    sections.append(
        DiagnosticSection(
            name="sandbox_pilot_flow",
            status="ready" if settings.sandbox_pilot_flow_enabled else "blocked",
            summary={
                "enabled": settings.sandbox_pilot_flow_enabled,
                "selected_mode": settings.usage_mode,
                "production_allowed": settings.sandbox_pilot_flow_allow_production,
                "real_ids_allowed": settings.sandbox_pilot_flow_allow_real_ids,
                "real_identities_allowed": (settings.sandbox_pilot_flow_allow_real_identities),
                "external_connection": False,
                "pilot_approved": False,
            },
        )
    )
    return sections


def sanitize_diagnostics_report(report: OperatorDiagnosticsReport) -> dict[str, Any]:
    return redact_diagnostic_value(report.model_dump(mode="json"))


def validate_diagnostics_report_safe(report: OperatorDiagnosticsReport | dict[str, Any]) -> None:
    value = (
        report.model_dump(mode="json") if isinstance(report, OperatorDiagnosticsReport) else report
    )
    try:
        assert_diagnostics_safe(value)
    except DiagnosticRedactionError as exc:
        raise OperatorDiagnosticsBlockedError(
            "Operator diagnostics failed strict redaction validation."
        ) from exc


def build_operator_diagnostics_report(
    settings: Settings,
    db_session: Session | None = None,
    app: FastAPI | None = None,
) -> OperatorDiagnosticsReport:
    if not settings.operator_diagnostics_enabled:
        raise OperatorDiagnosticsBlockedError("Operator diagnostics are disabled.")
    if (
        settings.support_bundle_include_raw_logs
        or settings.support_bundle_include_db_file
        or settings.support_bundle_include_attachments
        or settings.support_bundle_include_payloads
        or settings.operator_diagnostics_include_env_key_names
        or settings.operator_diagnostics_allow_local_paths
    ):
        raise OperatorDiagnosticsBlockedError(
            "Operator diagnostics blocked by unsafe inclusion settings."
        )
    runtime = collect_runtime_summary(settings)
    dependencies = collect_dependency_summary(settings)
    routes = (
        collect_route_inventory(app)
        if settings.operator_diagnostics_include_route_inventory
        else RouteDiagnosticSummary(available=False)
    )
    database = (
        collect_database_summary(db_session)
        if settings.operator_diagnostics_include_db_counts
        else DatabaseDiagnosticSummary(available=False)
    )
    queue = (
        collect_queue_summary(db_session)
        if settings.operator_diagnostics_include_db_counts
        else QueueDiagnosticSummary(available=False)
    )
    configuration = collect_configuration_summary(settings)
    safety = collect_safety_summary(settings)
    sections = collect_existing_readiness_summaries(settings, db_session)
    findings = (
        [
            DiagnosticFinding(
                code="database_unavailable",
                severity=DiagnosticSeverity.INFO,
                message=(
                    "Database aggregate counts were not requested or no local session was supplied."
                ),
            )
        ]
        if not database.available
        else []
    )
    draft = {
        "runtime": runtime.model_dump(mode="json"),
        "dependencies": dependencies.model_dump(mode="json"),
        "routes": routes.model_dump(mode="json"),
        "database": database.model_dump(mode="json"),
        "queue": queue.model_dump(mode="json"),
        "configuration": configuration.model_dump(mode="json"),
        "safety": safety.model_dump(mode="json"),
        "sections": [section.model_dump(mode="json") for section in sections],
        "findings": [finding.model_dump(mode="json") for finding in findings],
    }
    redaction_summary = summarize_redaction(draft, redact_diagnostic_value(draft))
    report = OperatorDiagnosticsReport(
        generated_at=datetime.now(UTC),
        environment=settings.environment,
        app_version=APP_VERSION,
        diagnostics_enabled=True,
        runtime=runtime,
        dependencies=dependencies,
        routes=routes,
        database=database,
        queue=queue,
        configuration=configuration,
        safety=safety,
        sections=sections,
        findings=findings[: settings.operator_diagnostics_max_findings],
        redaction=RedactionDiagnosticSummary(
            strict=settings.operator_diagnostics_redaction_strict,
            redacted_count=redaction_summary["redacted_count"],
            safe=redaction_summary["safe"],
            patterns_detected=[],
        ),
    )
    if settings.operator_diagnostics_redaction_strict:
        validate_diagnostics_report_safe(report)
    return report

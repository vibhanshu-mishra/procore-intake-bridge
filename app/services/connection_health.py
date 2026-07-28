from typing import Literal

from app.config import Settings, get_settings
from app.models.connections import DMSAConnection
from app.schemas.health import ConnectionHealthResult
from app.security.secret_provider import SecretProvider, get_secret_provider
from app.services import procore_client


def check_connection_health(
    connection: DMSAConnection,
    mode: Literal["mock", "live"] = "mock",
    settings: Settings | None = None,
    secret_provider: SecretProvider | None = None,
) -> ConnectionHealthResult:
    resolved_settings = settings or get_settings()
    if mode == "mock":
        return _mock_health(connection, resolved_settings)
    if not resolved_settings.procore_live_mode_enabled:
        return _disabled_live_health(connection)
    return _live_health(
        connection,
        resolved_settings,
        secret_provider or get_secret_provider(resolved_settings),
    )


def _mock_health(
    connection: DMSAConnection, settings: Settings
) -> ConnectionHealthResult:
    projects = {
        project_id: "mock_access_confirmed"
        for project_id in connection.permitted_project_ids
    }
    return ConnectionHealthResult(
        mode="mock",
        live_mode_enabled=settings.procore_live_mode_enabled,
        secret_reference_present=bool(connection.secret_name),
        secret_resolved=False,
        pyprocore_client_buildable=False,
        token_check="mock_valid",
        company_access="mock_access_confirmed",
        project_access=projects,
        rfi_access="mock_read_only",
        submittal_access="mock_read_only",
        attachment_visibility="mock_visible_from_parent_items",
        webhook_status="not_configured",
        polling_status="fixture_ready",
        findings=[
            "Fixture-mode result only; no credential value was resolved.",
            "No live Procore request was made.",
        ],
    )


def _disabled_live_health(connection: DMSAConnection) -> ConnectionHealthResult:
    return ConnectionHealthResult(
        mode="live_gated",
        live_mode_enabled=False,
        secret_reference_present=bool(connection.secret_name),
        secret_resolved=False,
        pyprocore_client_buildable=False,
        token_check="disabled",
        company_access="not_checked",
        project_access={
            project_id: "not_checked" for project_id in connection.permitted_project_ids
        },
        rfi_access="not_checked",
        submittal_access="not_checked",
        attachment_visibility="not_checked",
        webhook_status="not_configured",
        polling_status="fixture_only",
        findings=[
            "Live health checks are disabled by configuration.",
            "No secret was resolved and no live Procore request was made.",
        ],
    )


def _live_health(
    connection: DMSAConnection,
    settings: Settings,
    secret_provider: SecretProvider,
) -> ConnectionHealthResult:
    project_access = {
        project_id: "not_checked" for project_id in connection.permitted_project_ids
    }
    common = {
        "mode": "live_gated",
        "live_mode_enabled": True,
        "secret_reference_present": bool(connection.secret_name),
        "attachment_visibility": "not_proven_by_metadata_check",
        "webhook_status": "not_configured",
        "polling_status": "not_configured",
    }
    try:
        procore_client.get_dmsa_credentials_for_connection(connection, secret_provider)
    except Exception as exc:
        return ConnectionHealthResult(
            **common,
            secret_resolved=False,
            pyprocore_client_buildable=False,
            token_check="credential_resolution_failed",
            company_access="not_checked",
            project_access=project_access,
            rfi_access="not_checked",
            submittal_access="not_checked",
            findings=[f"Credential references could not be resolved ({type(exc).__name__})."],
        )

    try:
        client = procore_client.build_pyprocore_client_for_connection(
            connection, settings, secret_provider
        )
    except Exception as exc:
        return ConnectionHealthResult(
            **common,
            secret_resolved=True,
            pyprocore_client_buildable=False,
            token_check="client_build_failed",
            company_access="not_checked",
            project_access=project_access,
            rfi_access="not_checked",
            submittal_access="not_checked",
            findings=[f"PyProcore client construction failed ({type(exc).__name__})."],
        )

    findings = [
        "Credential references resolved and the PyProcore client was constructed.",
        "Checks are read-only and limited to the configured project allowlist.",
    ]
    rfi_results = []
    submittal_results = []
    for project_id in connection.permitted_project_ids:
        try:
            procore_client.check_project_access(client, connection, project_id)
            project_access[project_id] = "accessible"
            rfi_results.append(
                procore_client.check_rfi_access(client, connection, project_id)
            )
            submittal_results.append(
                procore_client.check_submittal_access(client, connection, project_id)
            )
        except Exception as exc:
            project_access[project_id] = "denied_or_unavailable"
            findings.append(
                f"Project access check failed for an allowlisted project ({type(exc).__name__})."
            )

    all_projects = all(value == "accessible" for value in project_access.values())
    return ConnectionHealthResult(
        **common,
        secret_resolved=True,
        pyprocore_client_buildable=True,
        token_check="client_credentials_path_buildable",
        company_access="inferred_from_project_checks" if all_projects else "degraded",
        project_access=project_access,
        rfi_access="readable" if rfi_results and all(rfi_results) else "degraded",
        submittal_access=(
            "readable" if submittal_results and all(submittal_results) else "degraded"
        ),
        findings=findings,
    )

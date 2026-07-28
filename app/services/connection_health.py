from app.models.connections import DMSAConnection
from app.schemas.health import ConnectionHealthResult


def check_connection_health(connection: DMSAConnection) -> ConnectionHealthResult:
    """Return deterministic fixture-mode checks without resolving secrets or making requests."""
    projects = {
        project_id: "mock_access_confirmed"
        for project_id in connection.permitted_project_ids
    }
    return ConnectionHealthResult(
        token_check="mock_valid",
        company_access="mock_access_confirmed",
        project_access=projects,
        rfi_access="mock_read_only",
        submittal_access="mock_read_only",
        attachment_visibility="mock_visible_from_parent_items",
        webhook_status="not_configured",
        polling_status="fixture_ready",
        findings=[
            "Fixture-mode result only; no token was resolved.",
            "No live Procore request was made.",
        ],
    )

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.connections import DMSAConnection


class LiveProcoreDisabled(RuntimeError):
    """Live Procore access is intentionally unavailable in Phase A1."""


def build_pyprocore_client_for_connection(_connection: DMSAConnection) -> Any:
    """Production seam for PyProcore; deliberately guarded during Phase A1."""
    raise LiveProcoreDisabled(
        "Live PyProcore clients are disabled in Phase A1. APP_PROCORE_MODE must remain fixture."
    )


def _load_fixture(filename: str, fixture_dir: Path | None = None) -> list[dict]:
    directory = fixture_dir or get_settings().fixture_dir
    return json.loads((directory / filename).read_text())


def _filtered(
    items: list[dict], project_id: str, updated_after: datetime | None
) -> list[dict]:
    result = [item for item in items if str(item["project_id"]) == str(project_id)]
    if updated_after:
        result = [
            item
            for item in result
            if datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")) > updated_after
        ]
    return result


def _assert_fixture_mode() -> None:
    if get_settings().procore_mode != "fixture":
        raise LiveProcoreDisabled("Live Procore API calls are disabled in Phase A1.")


def list_rfis_for_project(
    connection: DMSAConnection,
    project_id: str,
    updated_after: datetime | None = None,
    fixture_dir: Path | None = None,
) -> list[dict]:
    _assert_fixture_mode()
    _validate_project(connection, project_id)
    return _filtered(_load_fixture("fake_rfis.json", fixture_dir), project_id, updated_after)


def list_submittals_for_project(
    connection: DMSAConnection,
    project_id: str,
    updated_after: datetime | None = None,
    fixture_dir: Path | None = None,
) -> list[dict]:
    _assert_fixture_mode()
    _validate_project(connection, project_id)
    return _filtered(_load_fixture("fake_submittals.json", fixture_dir), project_id, updated_after)


def _validate_project(connection: DMSAConnection, project_id: str) -> None:
    if str(project_id) not in connection.permitted_project_ids:
        raise ValueError("Project is outside this connection's permitted project allowlist.")

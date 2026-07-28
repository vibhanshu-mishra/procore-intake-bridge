import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from app.config import Settings, get_settings
from app.models.connections import DMSAConnection
from app.security.secret_provider import SecretProvider


class LiveProcoreDisabledError(RuntimeError):
    """Live Procore access is disabled unless the explicit opt-in flag is true."""


# Phase A1 compatibility name.
LiveProcoreDisabled = LiveProcoreDisabledError


@dataclass(frozen=True)
class DMSACredentials:
    client_id: SecretStr
    client_secret: SecretStr


def get_dmsa_credentials_for_connection(
    connection: DMSAConnection, secret_provider: SecretProvider
) -> DMSACredentials:
    if not connection.client_id_ref:
        raise ValueError("A client_id_ref is required for live DMSA access.")
    return DMSACredentials(
        client_id=SecretStr(secret_provider.get_secret(connection.client_id_ref)),
        client_secret=SecretStr(secret_provider.get_secret(connection.secret_name)),
    )


def build_pyprocore_client_for_connection(
    connection: DMSAConnection,
    settings: Settings | None = None,
    secret_provider: SecretProvider | None = None,
) -> Any:
    resolved_settings = settings or get_settings()
    if not resolved_settings.procore_live_mode_enabled:
        raise LiveProcoreDisabledError(
            "Live Procore access is disabled. Set PROCORE_INTAKE_LIVE_MODE_ENABLED=true "
            "only in an approved runtime."
        )
    if secret_provider is None:
        from app.security.secret_provider import get_secret_provider

        secret_provider = get_secret_provider(resolved_settings)
    credentials = get_dmsa_credentials_for_connection(connection, secret_provider)
    return _instantiate_pyprocore_client(connection, credentials, resolved_settings)


def _instantiate_pyprocore_client(
    connection: DMSAConnection,
    credentials: DMSACredentials,
    settings: Settings,
) -> Any:
    """Construct one injected PyProcore HTTP client without making a network request."""
    from pyprocore.auth.token_manager import TokenManager
    from pyprocore.core.client import ProcoreClient
    from pyprocore.core.config import AuthMode, ProcoreSettings

    sdk_settings = ProcoreSettings(
        client_id=credentials.client_id.get_secret_value(),
        client_secret=credentials.client_secret,
        login_url=settings.procore_login_url,
        api_base=settings.procore_api_base,
        company_id=int(connection.procore_company_id),
        auth_mode=AuthMode.CLIENT_CREDENTIALS,
        token_store_backend="memory",
    )
    token_manager = TokenManager(settings=sdk_settings)
    return ProcoreClient(
        settings=sdk_settings,
        token_manager=token_manager,
        timeout_seconds=settings.procore_request_timeout_seconds,
    )


def check_project_access(client: Any, connection: DMSAConnection, project_id: str) -> bool:
    _validate_project(connection, project_id)
    client.get(f"/rest/v1.0/projects/{int(project_id)}")
    return True


def check_rfi_access(client: Any, connection: DMSAConnection, project_id: str) -> bool:
    _validate_project(connection, project_id)
    if "rfis" not in connection.enabled_tools:
        return False
    client.get_all(
        f"/rest/v1.0/projects/{int(project_id)}/rfis",
        params={"per_page": 1},
    )
    return True


def check_submittal_access(client: Any, connection: DMSAConnection, project_id: str) -> bool:
    _validate_project(connection, project_id)
    if "submittals" not in connection.enabled_tools:
        return False
    client.get_all(
        f"/rest/v1.0/projects/{int(project_id)}/submittals",
        params={"per_page": 1},
    )
    return True


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
        raise LiveProcoreDisabledError(
            "Fixture sync is the only supported sync mode in Phase A2."
        )


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

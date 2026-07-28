from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.connections import DMSAConnection
from app.security.admin_access import primary_admin_ref, rotation_admin_ref
from app.security.secret_provider_factory import build_secret_provider
from app.security.secret_refs import mask_secret_ref
from app.security.secrets import SecretProviderError


class SecretInventoryItem(BaseModel):
    purpose: str
    source: str
    required_when: str
    masked_ref: str
    status: Literal["unknown", "present", "missing"]


def _item(
    settings: Settings,
    ref: str,
    purpose: str,
    source: str,
    required_when: str,
) -> SecretInventoryItem:
    return SecretInventoryItem(
        purpose=purpose,
        source=source,
        required_when=required_when,
        masked_ref=mask_secret_ref(ref, settings),
        status="unknown",
    )


def collect_connection_secret_refs(
    settings: Settings, db_session: Session
) -> list[SecretInventoryItem]:
    items: list[SecretInventoryItem] = []
    for connection in db_session.scalars(select(DMSAConnection)):
        if connection.client_id_ref:
            items.append(
                _item(
                    settings,
                    connection.client_id_ref,
                    "DMSA client ID",
                    f"connection:{connection.id}",
                    "live DMSA read access",
                )
            )
        if connection.secret_name:
            items.append(
                _item(
                    settings,
                    connection.secret_name,
                    "DMSA client secret",
                    f"connection:{connection.id}",
                    "live DMSA read access",
                )
            )
    return items


def collect_webhook_secret_refs(settings: Settings) -> list[SecretInventoryItem]:
    if not (
        settings.webhooks_enabled
        and settings.require_webhook_signature
        and settings.webhook_secret_name
    ):
        return []
    return [
        _item(
            settings,
            settings.webhook_secret_name,
            "Webhook signature",
            "settings",
            "signed webhook receiving",
        )
    ]


def collect_admin_secret_refs(settings: Settings) -> list[SecretInventoryItem]:
    primary = primary_admin_ref(settings)
    rotation = rotation_admin_ref(settings)
    if not settings.admin_dashboard_enabled or not (primary or rotation):
        return []
    items: list[SecretInventoryItem] = []
    if primary:
        items.append(
            _item(
                settings,
                primary,
                "admin_auth_primary_token",
                "settings",
                "token-required admin and protected deployment routes",
            )
        )
    if rotation:
        items.append(
            _item(
                settings,
                rotation,
                "admin_auth_rotation_token",
                "settings",
                "temporary admin token rotation overlap",
            )
        )
    return items


def collect_sandbox_smoke_secret_refs(
    settings: Settings, db_session: Session | None = None
) -> list[SecretInventoryItem]:
    if not settings.sandbox_smoke_enabled or db_session is None:
        return []
    connection_id = settings.sandbox_smoke_connection_id
    if connection_id is None:
        return []
    connection = db_session.get(DMSAConnection, connection_id)
    if connection is None:
        return []
    return collect_connection_secret_refs(settings, db_session)


def collect_required_secret_refs(
    settings: Settings,
    db_session: Session | None = None,
    run_health: bool = False,
) -> list[SecretInventoryItem]:
    items = collect_webhook_secret_refs(settings) + collect_admin_secret_refs(settings)
    if db_session is not None:
        items.extend(collect_connection_secret_refs(settings, db_session))
    unique: dict[tuple[str, str], SecretInventoryItem] = {
        (item.masked_ref, item.purpose): item for item in items
    }
    result = list(unique.values())
    if not run_health or not settings.secret_health_check_enabled:
        return result
    try:
        provider = build_secret_provider(settings)
    except SecretProviderError:
        return [item.model_copy(update={"status": "missing"}) for item in result]
    checked: list[SecretInventoryItem] = []
    for item in result:
        # Provider checks require the original ref, so match the source list without exposing it.
        original = next(
            candidate
            for candidate in items
            if candidate.masked_ref == item.masked_ref
            and candidate.purpose == item.purpose
        )
        raw_ref = _resolve_raw_ref(settings, db_session, original)
        present = bool(raw_ref) and provider.has_secret(raw_ref)
        checked.append(
            item.model_copy(update={"status": "present" if present else "missing"})
        )
    return checked


def _resolve_raw_ref(
    settings: Settings,
    db_session: Session | None,
    item: SecretInventoryItem,
) -> str | None:
    if item.purpose == "Webhook signature":
        return settings.webhook_secret_name
    if item.purpose == "admin_auth_primary_token":
        return primary_admin_ref(settings)
    if item.purpose == "admin_auth_rotation_token":
        return rotation_admin_ref(settings)
    if db_session is None or not item.source.startswith("connection:"):
        return None
    connection = db_session.get(DMSAConnection, int(item.source.split(":", 1)[1]))
    if connection is None:
        return None
    return (
        connection.client_id_ref
        if item.purpose == "DMSA client ID"
        else connection.secret_name
    )

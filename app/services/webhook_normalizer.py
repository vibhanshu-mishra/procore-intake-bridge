import hashlib
import json
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEY_MARKERS = (
    "authorization",
    "signature",
    "secret",
    "token",
    "password",
    "credential",
    "url",
)


def normalize_procore_webhook_event(
    payload: dict[str, Any], headers: Mapping[str, str]
) -> dict[str, Any]:
    event_type = str(
        _first(payload, "event_type", "eventType", "type")
        or _nested(payload, "event", "name")
        or "unknown"
    )
    resource_type = infer_resource_type(payload)
    action = infer_action(payload)
    project_id = infer_project_id(payload)
    item_id = infer_item_id(payload)
    company_id = _find_id(payload, "company_id", "companyId", container="company")
    event_id = extract_event_id(payload, headers) or build_event_fingerprint(payload)
    return {
        "source": "procore",
        "event_id": event_id,
        "event_type": event_type[:200],
        "resource_type": resource_type,
        "action": action,
        "procore_company_id": _string_or_none(company_id),
        "procore_project_id": _string_or_none(project_id),
        "procore_item_id": _string_or_none(item_id),
    }


def infer_resource_type(payload: dict[str, Any]) -> str:
    candidates = [
        _first(payload, "resource_type", "resourceType"),
        _nested(payload, "resource", "type"),
        _first(payload, "event_type", "eventType", "type"),
        _nested(payload, "event", "name"),
    ]
    keys = {key.casefold() for key in _all_keys(payload)}
    text = " ".join(str(value).casefold() for value in candidates if value)
    if "rfi" in text or "rfi_id" in keys or "rfiid" in keys:
        return "rfi"
    if (
        "submittal" in text
        or "submittal_id" in keys
        or "submittalid" in keys
    ):
        return "submittal"
    return "unknown"


def infer_action(payload: dict[str, Any]) -> str:
    candidates = [
        _first(payload, "action"),
        _nested(payload, "payload", "action"),
        _first(payload, "event_type", "eventType", "type"),
        _nested(payload, "event", "name"),
    ]
    text = " ".join(str(value).casefold() for value in candidates if value)
    for action in ("created", "updated", "deleted"):
        if action in text or action.removesuffix("d") in text:
            return action
    return "unknown"


def infer_project_id(payload: dict[str, Any]) -> str | None:
    return _string_or_none(
        _find_id(payload, "project_id", "projectId", container="project")
    )


def infer_item_id(payload: dict[str, Any]) -> str | None:
    resource_id = _nested(payload, "resource", "id")
    if resource_id is not None:
        return str(resource_id)
    for key in ("rfi_id", "rfiId", "submittal_id", "submittalId", "resource_id"):
        value = _find_recursive(payload, key)
        if value is not None:
            return str(value)
    return None


def extract_event_id(
    payload: dict[str, Any], headers: Mapping[str, str]
) -> str | None:
    for key, value in headers.items():
        normalized = key.casefold().replace("_", "-")
        if normalized.endswith("event-id") and value.strip():
            return value.strip()[:128]
    value = (
        _first(payload, "event_id", "eventId", "delivery_id", "deliveryId")
        or _nested(payload, "event", "id")
    )
    if value is None and _first(payload, "event_type", "eventType", "type"):
        value = payload.get("id")
    return str(value)[:128] if value is not None else None


def build_event_fingerprint(payload: dict[str, Any]) -> str:
    safe_payload = sanitize_payload(payload)
    canonical = json.dumps(
        safe_payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return f"fp-{hashlib.sha256(canonical).hexdigest()}"


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(marker in str(key).casefold() for marker in SENSITIVE_KEY_MARKERS)
                else sanitize_payload(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _find_id(
    payload: dict[str, Any], *keys: str, container: str
) -> Any:
    for key in keys:
        value = _find_recursive(payload, key)
        if value is not None:
            return value
    return _find_recursive_container_id(payload, container)


def _find_recursive(value: Any, target: str) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() == target.casefold():
                return item
        for item in value.values():
            found = _find_recursive(item, target)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_recursive(item, target)
            if found is not None:
                return found
    return None


def _find_recursive_container_id(value: Any, container: str) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                key.casefold() == container.casefold()
                and isinstance(item, dict)
                and item.get("id") is not None
            ):
                return item["id"]
        for item in value.values():
            found = _find_recursive_container_id(item, container)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_recursive_container_id(item, container)
            if found is not None:
                return found
    return None


def _all_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _all_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_keys(item)


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if payload.get(key) is not None:
            return payload[key]
    return None


def _nested(payload: dict[str, Any], container: str, key: str) -> Any:
    value = payload.get(container)
    return value.get(key) if isinstance(value, dict) else None


def _string_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None

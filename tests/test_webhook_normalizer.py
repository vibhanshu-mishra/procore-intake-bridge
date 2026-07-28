import json
from pathlib import Path

import pytest

from app.services.webhook_normalizer import (
    build_event_fingerprint,
    normalize_procore_webhook_event,
)

FIXTURES = Path("app/fixtures/webhooks")


def load(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize(
    ("filename", "resource_type", "action"),
    [
        ("rfi_created.json", "rfi", "created"),
        ("rfi_updated.json", "rfi", "updated"),
        ("submittal_created.json", "submittal", "created"),
        ("submittal_updated.json", "submittal", "updated"),
    ],
)
def test_known_fixture_normalizes(filename, resource_type, action):
    result = normalize_procore_webhook_event(load(filename), {})
    assert result["resource_type"] == resource_type
    assert result["action"] == action
    assert result["procore_project_id"] == "project-1001"
    assert result["procore_item_id"] is not None


def test_unknown_fixture_does_not_crash():
    result = normalize_procore_webhook_event(load("unknown_event.json"), {})
    assert result["resource_type"] == "unknown"
    assert result["event_id"] == "evt-unknown-001"


def test_event_id_header_and_fingerprint_fallback():
    payload = {"notice": "synthetic", "project_id": "project-placeholder"}
    result = normalize_procore_webhook_event(
        payload, {"custom-event-id": "header-event-001"}
    )
    assert result["event_id"] == "header-event-001"
    first = build_event_fingerprint(payload)
    second = build_event_fingerprint(dict(reversed(list(payload.items()))))
    assert first == second
    assert first.startswith("fp-")

import hashlib
import hmac
import json
from pathlib import Path

from sqlalchemy import func, select

from app.config import Settings
from app.models.webhook_events import WebhookEvent
from app.routers import webhooks

FIXTURES = Path("app/fixtures/webhooks")


def load(name):
    return json.loads((FIXTURES / name).read_text())


def event_count(session):
    return session.scalar(select(func.count()).select_from(WebhookEvent))


def test_webhook_dry_run_does_not_persist(client, db_session):
    response = client.post("/webhooks/procore/dry-run", json=load("rfi_created.json"))
    assert response.status_code == 200
    assert response.json()["persisted"] is False
    assert event_count(db_session) == 0


def test_receiver_persists_rfi_and_submittal(client, db_session):
    rfi = client.post("/webhooks/procore", json=load("rfi_created.json"))
    submittal = client.post(
        "/webhooks/procore", json=load("submittal_created.json")
    )
    assert rfi.status_code == 200
    assert rfi.json()["processing_status"] == "queued"
    assert submittal.json()["resource_type"] == "submittal"
    assert event_count(db_session) == 2


def test_duplicate_event_is_idempotent(client, db_session):
    payload = load("rfi_updated.json")
    first = client.post("/webhooks/procore", json=payload)
    second = client.post("/webhooks/procore", json=payload)
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert event_count(db_session) == 1


def test_unknown_event_is_stored_skipped(client, db_session):
    response = client.post("/webhooks/procore", json=load("unknown_event.json"))
    assert response.status_code == 200
    assert response.json()["processing_status"] == "skipped"
    event = db_session.scalar(select(WebhookEvent))
    assert event.resource_type == "unknown"


def test_required_invalid_signature_rejected(monkeypatch, client, db_session):
    settings = Settings(
        _env_file=None,
        require_webhook_signature=True,
        webhook_secret_name="webhook_test",
    )
    monkeypatch.setattr(webhooks, "get_settings", lambda: settings)
    monkeypatch.setenv("PROCORE_INTAKE_SECRET_WEBHOOK_TEST", "fake-secret")
    response = client.post(
        "/webhooks/procore",
        json=load("rfi_created.json"),
        headers={"x-procore-signature": "invalid"},
    )
    assert response.status_code == 401
    assert event_count(db_session) == 0


def test_required_valid_signature_and_safe_response(monkeypatch, client):
    secret = "fake-local-secret-never-return"
    payload = load("rfi_created.json")
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    settings = Settings(
        _env_file=None,
        require_webhook_signature=True,
        webhook_secret_name="webhook_test",
        webhook_signature_header="x-test-signature",
    )
    monkeypatch.setattr(webhooks, "get_settings", lambda: settings)
    monkeypatch.setenv("PROCORE_INTAKE_SECRET_WEBHOOK_TEST", secret)
    response = client.post(
        "/webhooks/procore",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-test-signature": signature,
            "authorization": "Bearer must-not-return",
        },
    )
    assert response.status_code == 200
    assert response.json()["signature_status"] == "valid"
    assert secret not in response.text
    assert "must-not-return" not in response.text


def test_event_listing_detail_and_replay(client):
    receipt = client.post("/webhooks/procore", json=load("rfi_created.json")).json()
    event_id = receipt["webhook_event_id"]
    assert client.get("/webhook-events").json()[0]["id"] == event_id
    detail = client.get(f"/webhook-events/{event_id}")
    assert detail.status_code == 200
    assert "payload_json" not in detail.json()
    replay = client.post(f"/webhook-events/{event_id}/replay")
    assert replay.status_code == 200
    assert replay.json()["processing_status"] == "queued"


def test_sensitive_payload_fields_are_redacted(client, db_session):
    payload = load("rfi_created.json")
    payload["authorization"] = "Bearer raw-secret-value"
    payload["metadata"] = {
        "access_token": "raw-token-value",
        "attachment_url": "https://example.invalid/raw-signed-url",
    }
    response = client.post("/webhooks/procore", json=payload)
    assert response.status_code == 200
    event = db_session.scalar(select(WebhookEvent))
    serialized = json.dumps(event.payload_json)
    assert "raw-secret-value" not in serialized
    assert "raw-token-value" not in serialized
    assert "raw-signed-url" not in serialized


def test_receiver_does_not_create_attachment_files(tmp_path, client):
    response = client.post("/webhooks/procore", json=load("rfi_created.json"))
    assert response.status_code == 200
    assert list(tmp_path.rglob("*")) == []

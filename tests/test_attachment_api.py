from sqlalchemy import func, select

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.services import attachment_storage


def plan_payload():
    return {
        "connection_id": None,
        "source_type": "rfi",
        "procore_project_id": "project-placeholder",
        "procore_item_id": "rfi-placeholder",
        "procore_attachment_id": "attachment-placeholder",
        "original_filename": "../../fixture drawing.pdf",
        "content_type": "application/pdf",
        "source_url": "https://example.invalid/fake-signed-url",
    }


def test_plan_list_get_exclude_raw_url(client, db_session):
    raw_url = plan_payload()["source_url"]
    response = client.post("/attachments/plan", json=plan_payload())
    assert response.status_code == 200
    payload = response.json()
    assert payload["persisted"] is True
    assert payload["safe_filename"] == "fixture_drawing.pdf"
    assert raw_url not in response.text
    attachment_id = payload["attachment_id"]
    listing = client.get("/attachments")
    detail = client.get(f"/attachments/{attachment_id}")
    assert listing.status_code == 200
    assert detail.status_code == 200
    assert raw_url not in listing.text
    assert raw_url not in detail.text


def test_fixture_download_api_writes_local_fake_file(
    monkeypatch, tmp_path, client, db_session
):
    config = Settings(
        _env_file=None,
        attachment_storage_root=tmp_path,
        attachment_allow_overwrite=False,
    )
    monkeypatch.setattr(attachment_storage, "get_settings", lambda: config)
    attachment_id = client.post(
        "/attachments/plan", json=plan_payload()
    ).json()["attachment_id"]
    response = client.post(
        f"/attachments/{attachment_id}/fixture-download",
        json={"fixture_label": "api-test"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["download_status"] == "downloaded"
    assert len(payload["checksum_sha256"]) == 64
    assert not payload["storage_path"].startswith("/")
    assert (tmp_path / payload["storage_key"]).exists()
    second = client.post(
        f"/attachments/{attachment_id}/fixture-download"
    )
    assert second.status_code == 409


def test_intake_record_attachments_route(client, db_session, connection):
    run = client.post(f"/connections/{connection.id}/sync/run")
    assert run.status_code == 200
    attachment = db_session.scalar(select(AttachmentObject))
    response = client.get(
        f"/intake-records/{attachment.intake_record_id}/attachments"
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_plan_creates_one_manifest_row(client, db_session):
    client.post("/attachments/plan", json=plan_payload())
    assert (
        db_session.scalar(select(func.count()).select_from(AttachmentObject))
        == 1
    )

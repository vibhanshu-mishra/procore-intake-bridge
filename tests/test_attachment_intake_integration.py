import json

from sqlalchemy import func, select

from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.services.intake_sync import sync_connection


def test_sync_dry_run_returns_plans_without_rows(db_session, connection):
    summary = sync_connection(db_session, connection, dry_run=True)
    assert len(summary.attachment_plans) == 3
    assert all(not plan.persisted for plan in summary.attachment_plans)
    assert (
        db_session.scalar(select(func.count()).select_from(AttachmentObject))
        == 0
    )


def test_sync_run_creates_rfi_and_submittal_manifests(
    db_session, connection
):
    summary = sync_connection(db_session, connection, dry_run=False)
    objects = list(
        db_session.scalars(select(AttachmentObject).order_by(AttachmentObject.id))
    )
    assert len(summary.attachment_plans) == 3
    assert len(objects) == 3
    assert {item.source_type for item in objects} == {"rfi", "submittal"}
    assert all(item.download_status == "planned" for item in objects)
    assert sum(item.source_url_present for item in objects) == 2
    assert all(
        item.source_url_hash
        for item in objects
        if item.source_url_present
    )


def test_raw_intake_payload_does_not_store_source_urls(
    db_session, connection
):
    sync_connection(db_session, connection, dry_run=False)
    serialized = json.dumps(
        [record.raw_payload_json for record in db_session.scalars(select(IntakeRecord))]
    )
    assert "example.invalid" not in serialized
    assert "source_url" in serialized
    assert "[REDACTED]" in serialized

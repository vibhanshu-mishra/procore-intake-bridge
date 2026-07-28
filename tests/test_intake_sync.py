from sqlalchemy import func, select

from app.models.intake_records import IntakeAttachment, IntakeRecord
from app.services.intake_sync import collect_fixture_records, sync_connection


def test_fixture_records_normalize(connection):
    records, manifest = collect_fixture_records(connection)
    normalized = [record for _, record in records]
    rfi = next(record for record in normalized if record.source_type == "rfi")
    submittal = next(record for record in normalized if record.source_type == "submittal")
    assert rfi.number == "RFI-001"
    assert rfi.title == "Confirm slab edge detail"
    assert submittal.number == "SUB-014"
    assert submittal.attachment_count == 2
    assert {entry.filename for entry in manifest} == {
        "slab-edge.pdf",
        "steel-shops.pdf",
        "transmittal.txt",
    }


def test_dry_run_does_not_write(db_session, connection):
    summary = sync_connection(db_session, connection, dry_run=True)
    assert summary.dry_run is True
    assert summary.record_count == 2
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 0


def test_run_writes_fixture_records(db_session, connection):
    summary = sync_connection(db_session, connection, dry_run=False)
    assert summary.sync_run_id is not None
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 2
    assert db_session.scalar(select(func.count()).select_from(IntakeAttachment)) == 3


def test_api_dry_run_and_run(client, connection):
    dry = client.post(f"/connections/{connection.id}/sync/dry-run")
    assert dry.status_code == 200
    assert dry.json()["sync_run_id"] is None
    run = client.post(f"/connections/{connection.id}/sync/run")
    assert run.status_code == 200
    assert run.json()["record_count"] == 2

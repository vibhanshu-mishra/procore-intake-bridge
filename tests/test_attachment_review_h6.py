from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import run

import pytest

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.attachment_review import (
    AttachmentReviewAvailability,
    AttachmentReviewFileCategory,
    AttachmentReviewSort,
    AttachmentReviewStatus,
)
from app.services.attachment_review import (
    AttachmentReviewError,
    build_attachment_review_filter,
    build_attachment_review_workspace_summary,
    classify_attachment_file_category,
    get_attachment_review_record_detail,
    list_attachment_review_records,
    validate_attachment_review_response_safe,
)
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def _record(db_session, connection, *, suffix, tool="rfi", age=1, count=0):
    sync_run = SyncRun(
        connection_id=connection.id,
        mode="fixture",
        status="completed",
        record_count=1,
        attachment_count=count,
    )
    db_session.add(sync_run)
    db_session.flush()
    record = IntakeRecord(
        source_type=tool,
        procore_project_id=f"fake-project-{suffix}",
        procore_item_id=f"fake-item-{suffix}",
        number=f"FAKE-{suffix}",
        title=f"Synthetic attachment metadata {suffix}",
        status="open",
        received_at=datetime.now(UTC) - timedelta(hours=age),
        source_updated_at=datetime.now(UTC),
        raw_payload_json={"private_fixture": "must-not-appear"},
        attachment_count=count,
        sync_run_id=sync_run.id,
    )
    db_session.add(record)
    db_session.flush()
    return record


def _attachment(
    db_session,
    connection,
    record,
    *,
    suffix,
    content_type="application/pdf",
    status="planned",
    backend="local",
    checksum=None,
    source=True,
    size=100,
):
    value = AttachmentObject(
        intake_record_id=record.id,
        sync_run_id=record.sync_run_id,
        connection_id=connection.id,
        source_type=record.source_type,
        procore_project_id=record.procore_project_id,
        procore_item_id=record.procore_item_id,
        procore_attachment_id=f"fake-attachment-{suffix}",
        original_filename=f"private-{suffix}.pdf",
        safe_filename=f"private-{suffix}.pdf",
        content_type=content_type,
        size_bytes=size,
        source_url_present=source,
        source_url_hash="a" * 64 if source else None,
        storage_backend=backend,
        storage_key=f"private-key-{suffix}",
        storage_path=f"/private/example/{suffix}",
        checksum_sha256=checksum,
        download_status=status,
    )
    db_session.add(value)
    db_session.flush()
    return value


def test_empty_disabled_and_unsafe_configuration_fail_closed(db_session):
    summary = build_attachment_review_workspace_summary(db_session, _settings())
    assert summary.status is AttachmentReviewStatus.EMPTY
    assert summary.metadata_only is True
    assert summary.contents_available is False
    assert summary.storage_calls_made is False
    assert (
        build_attachment_review_workspace_summary(
            db_session, _settings(attachment_review_enabled=False)
        ).status
        is AttachmentReviewStatus.DISABLED
    )
    assert (
        build_attachment_review_workspace_summary(
            db_session, _settings(attachment_review_expose_storage_keys=True)
        ).status
        is AttachmentReviewStatus.NEEDS_CONFIGURATION
    )


def test_listing_is_bounded_filtered_and_deterministic(db_session, connection):
    old = _record(db_session, connection, suffix="old", age=20, count=2)
    recent = _record(db_session, connection, suffix="recent", tool="submittal", count=1)
    missing = _record(db_session, connection, suffix="missing", age=10)
    _attachment(db_session, connection, old, suffix="planned")
    _attachment(
        db_session,
        connection,
        recent,
        suffix="stored",
        status="downloaded",
        backend="fixture",
        checksum="b" * 64,
    )
    db_session.commit()
    settings = _settings(attachment_review_max_page_size=2)
    page = list_attachment_review_records(
        db_session,
        build_attachment_review_filter(
            settings,
            page_size=999,
            sort=AttachmentReviewSort.RECORD_RECEIVED_AT_DESC,
        ),
        settings,
    )
    assert page.page_size == 2
    assert page.total_items == 3
    assert page.items[0].record_id == recent.id
    present = list_attachment_review_records(
        db_session,
        build_attachment_review_filter(settings, availability="manifest_present", tool="rfi"),
        settings,
    )
    assert [item.record_id for item in present.items] == [old.id]
    absent = list_attachment_review_records(
        db_session,
        build_attachment_review_filter(settings, availability="manifest_missing"),
        settings,
    )
    assert [item.record_id for item in absent.items] == [missing.id]
    fixture = list_attachment_review_records(
        db_session,
        build_attachment_review_filter(settings, storage_status="fixture_metadata_available"),
        settings,
    )
    assert [item.record_id for item in fixture.items] == [recent.id]


def test_manifest_detail_summarizes_only_safe_metadata(db_session, connection):
    record = _record(db_session, connection, suffix="detail", count=4)
    _attachment(
        db_session,
        connection,
        record,
        suffix="stored",
        content_type="image/png",
        status="downloaded",
        checksum="c" * 64,
        size=512,
    )
    _attachment(
        db_session,
        connection,
        record,
        suffix="skipped",
        content_type="text/plain",
        status="skipped",
        source=False,
        size=None,
    )
    _attachment(
        db_session,
        connection,
        record,
        suffix="blocked",
        content_type="application/blocked",
        status="blocked",
    )
    db_session.commit()
    detail = get_attachment_review_record_detail(db_session, record.id, _settings())
    assert detail is not None
    assert detail.manifest.availability is AttachmentReviewAvailability.MANIFEST_PRESENT
    assert detail.manifest.manifest_count == 3
    assert detail.manifest.planned_count == 4
    assert detail.manifest.stored_metadata_count == 1
    assert detail.manifest.skipped_count == 1
    assert detail.manifest.blocked_count == 1
    assert detail.manifest.checksum_present_count == 1
    assert detail.manifest.source_available_count == 2
    assert detail.manifest.total_size_bytes == 612
    assert detail.items[0].file_category is AttachmentReviewFileCategory.IMAGE_LIKE
    serialized = detail.model_dump_json()
    for unsafe in (
        "private-stored.pdf",
        "private-key",
        "/private/example",
        record.procore_item_id,
        "source_url_hash",
        "checksum_sha256",
    ):
        assert unsafe not in serialized
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


@pytest.mark.parametrize(
    ("content_type", "category"),
    [
        ("application/pdf", AttachmentReviewFileCategory.PDF_LIKE),
        ("image/jpeg", AttachmentReviewFileCategory.IMAGE_LIKE),
        ("application/vnd.dwg", AttachmentReviewFileCategory.DRAWING_LIKE),
        ("application/vnd.ms-excel", AttachmentReviewFileCategory.SPREADSHEET_LIKE),
        ("text/plain", AttachmentReviewFileCategory.TEXT_LIKE),
        ("application/zip", AttachmentReviewFileCategory.ARCHIVE_LIKE),
        ("application/octet-stream", AttachmentReviewFileCategory.UNKNOWN),
        ("application/blocked", AttachmentReviewFileCategory.BLOCKED),
    ],
)
def test_file_category_uses_content_type_only(content_type, category):
    assert (
        classify_attachment_file_category(
            {"content_type": content_type, "original_filename": "ignored.pdf"},
            _settings(),
        )
        is category
    )


def test_all_sort_options_are_stable(db_session, connection):
    first = _record(db_session, connection, suffix="1", tool="rfi", count=1)
    second = _record(db_session, connection, suffix="2", tool="submittal", count=2)
    _attachment(db_session, connection, first, suffix="1")
    _attachment(db_session, connection, second, suffix="2", status="downloaded")
    db_session.commit()
    for sort in AttachmentReviewSort:
        page = list_attachment_review_records(
            db_session,
            build_attachment_review_filter(_settings(), sort=sort),
            _settings(),
        )
        assert sorted(item.record_id for item in page.items) == [first.id, second.id]


@pytest.mark.parametrize(
    "unsafe",
    [
        {"raw_payload_json": {"fixture": True}},
        {"source_url": "hidden"},
        {"signed_url": "hidden"},
        {"storage_key": "hidden"},
        {"message": "https://unsafe.invalid/value"},
        {"message": "/Users/example/private"},
        {"message": "private-live-name.pdf"},
        {"message": "client_secret=unsafe"},
    ],
)
def test_response_validator_blocks_unsafe_values(unsafe):
    with pytest.raises(AttachmentReviewError):
        validate_attachment_review_response_safe(unsafe)


def test_service_does_not_open_files_or_mutate(monkeypatch, db_session, connection):
    record = _record(db_session, connection, suffix="no-open", count=1)
    _attachment(db_session, connection, record, suffix="no-open")
    db_session.commit()

    def blocked_open(*args, **kwargs):
        raise AssertionError("file access is outside H6")

    monkeypatch.setattr("builtins.open", blocked_open)
    assert get_attachment_review_record_detail(db_session, record.id, _settings())
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_attachment_routes_are_get_only_safe_and_linked(client, db_session, connection):
    record = _record(db_session, connection, suffix="route", count=1)
    _attachment(db_session, connection, record, suffix="route")
    db_session.commit()
    paths = (
        "/review/attachments",
        f"/review/attachments/{record.id}",
        "/review/api/attachments",
        "/review/api/attachments/summary",
        f"/review/api/attachments/{record.id}",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        lowered = response.text.casefold()
        for unsafe in (
            "private-route.pdf",
            "private-key",
            "/private/example",
            record.procore_item_id.casefold(),
        ):
            assert unsafe not in lowered
    assert client.get("/review/api/attachments/99999").status_code == 404
    assert client.post("/review/api/attachments").status_code == 405
    assert f"/review/intake/{record.id}" in client.get(f"/review/attachments/{record.id}").text
    assert f"/review/attachments/{record.id}" in client.get(f"/review/intake/{record.id}").text
    assert not audit_routes()
    assert not any(
        "download" in route.path or "file" in route.path
        for route in application_routes()
        if route.path.startswith("/review/attachments")
    )


def test_cli_and_make_targets_are_safe():
    for command in (
        [".venv/bin/python", "scripts/check_attachment_review.py"],
        [".venv/bin/python", "scripts/print_attachment_review_summary.py"],
        ["make", "attachment-review-check"],
        ["make", "attachment-review-summary"],
    ):
        result = run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        output = result.stdout.casefold()
        assert "http://" not in output
        assert "https://" not in output
        assert "/users/" not in output

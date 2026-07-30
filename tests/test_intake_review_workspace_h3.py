from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import run

import pytest

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.intake_review_workspace import (
    IntakeReviewSort,
    IntakeReviewTool,
    IntakeReviewWorkspaceStatus,
)
from app.services.intake_review_workspace import (
    IntakeReviewWorkspaceError,
    build_intake_review_filter,
    build_intake_review_workspace_summary,
    get_intake_review_record_detail,
    list_intake_review_records,
    validate_intake_review_response_safe,
)

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def _record(db_session, connection, *, tool="rfi", suffix="1", received_at=None):
    sync_run = SyncRun(
        connection_id=connection.id,
        mode="fixture",
        status="completed",
        record_count=1,
        attachment_count=1,
    )
    db_session.add(sync_run)
    db_session.flush()
    record = IntakeRecord(
        source_type=tool,
        procore_project_id=f"fake-project-{suffix}",
        procore_item_id=f"fake-item-{suffix}",
        number=f"FAKE-{suffix}",
        title=f"Synthetic intake {suffix}",
        status="open",
        received_at=received_at or datetime.now(UTC),
        source_updated_at=datetime.now(UTC),
        raw_payload_json={"must_not_appear": "fixture-only"},
        attachment_count=1,
        sync_run_id=sync_run.id,
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_empty_workspace_summary_is_safe(db_session):
    summary = build_intake_review_workspace_summary(db_session, _settings())
    assert summary.status is IntakeReviewWorkspaceStatus.EMPTY
    assert summary.total_records == 0
    assert summary.read_only is True
    assert summary.procore_calls_made is False
    validate_intake_review_response_safe(summary)


def test_workspace_disabled_and_unsafe_configuration_fail_closed(db_session):
    disabled = _settings(intake_review_workspace_enabled=False)
    assert (
        build_intake_review_workspace_summary(db_session, disabled).status
        is IntakeReviewWorkspaceStatus.DISABLED
    )
    unsafe = _settings(intake_review_workspace_expose_raw_payloads=True)
    assert (
        build_intake_review_workspace_summary(db_session, unsafe).status
        is IntakeReviewWorkspaceStatus.NEEDS_CONFIGURATION
    )


def test_listing_is_bounded_filtered_and_deterministic(db_session, connection):
    older = _record(
        db_session,
        connection,
        tool="rfi",
        suffix="older",
        received_at=datetime.now(UTC) - timedelta(days=10),
    )
    newer = _record(db_session, connection, tool="rfi", suffix="newer")
    _record(db_session, connection, tool="submittal", suffix="submittal")
    db_session.commit()
    settings = _settings(intake_review_workspace_max_page_size=1)
    filters = build_intake_review_filter(
        settings,
        tool="rfi",
        page_size=500,
        sort=IntakeReviewSort.RECEIVED_AT_DESC,
    )
    page = list_intake_review_records(db_session, filters, settings)
    assert page.page_size == 1
    assert page.total_items == 2
    assert page.items[0].record_id == newer.id
    assert page.items[0].record_id != older.id
    assert page.tool_filter is IntakeReviewTool.RFI


def test_detail_masks_sources_summarizes_manifest_and_does_not_mutate(
    db_session, connection
):
    record = _record(db_session, connection)
    db_session.add(
        AttachmentObject(
            intake_record_id=record.id,
            sync_run_id=record.sync_run_id,
            connection_id=connection.id,
            source_type="rfi",
            procore_project_id=record.procore_project_id,
            procore_item_id=record.procore_item_id,
            procore_attachment_id="fake-attachment-1",
            original_filename="fixture.txt",
            safe_filename="fixture.txt",
            content_type="text/plain",
            size_bytes=12,
            source_url_present=True,
            source_url_hash="a" * 64,
            storage_backend="local",
            storage_key="private-key",
            storage_path="/private/example",
            checksum_sha256="b" * 64,
            download_status="planned",
        )
    )
    db_session.commit()
    detail = get_intake_review_record_detail(db_session, record.id, _settings())
    assert detail is not None
    assert detail.source_context.project_id_hash
    assert detail.source_context.project_id_masked.startswith("••••")
    assert detail.attachment_summary.manifest_count == 1
    assert detail.attachment_summary.checksum_count == 1
    assert detail.attachment_summary.contents_read is False
    serialized = detail.model_dump_json()
    assert record.procore_project_id not in serialized
    assert "storage_path" not in serialized
    assert "fixture.txt" not in serialized
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_unknown_tool_and_missing_detail_are_safe(db_session, connection):
    record = _record(db_session, connection, tool="other", suffix="unknown")
    db_session.commit()
    page = list_intake_review_records(
        db_session,
        build_intake_review_filter(_settings(), tool="unknown"),
        _settings(),
    )
    assert page.items[0].record_id == record.id
    assert page.items[0].tool is IntakeReviewTool.UNKNOWN
    assert get_intake_review_record_detail(db_session, 99999, _settings()) is None


@pytest.mark.parametrize(
    "unsafe",
    [
        {"raw_payload_json": {"value": "unsafe"}},
        {"source_url": "redacted"},
        {"message": "https://unsafe.invalid/value"},
        {"message": "/Users/example/private/value"},
        {"message": "client_secret=unsafe-value"},
    ],
)
def test_response_validator_blocks_unsafe_values(unsafe):
    with pytest.raises(IntakeReviewWorkspaceError):
        validate_intake_review_response_safe(unsafe)


def test_review_routes_are_get_only_and_safe(client, db_session, connection):
    record = _record(db_session, connection)
    db_session.commit()
    paths = (
        "/review",
        "/review/intake",
        f"/review/intake/{record.id}",
        "/review/api/summary",
        "/review/api/intake",
        f"/review/api/intake/{record.id}",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        lowered = response.text.casefold()
        assert "raw_payload_json" not in lowered
        assert record.procore_project_id.casefold() not in lowered
        assert "https://unsafe" not in lowered
    assert client.get("/review/api/intake/99999").status_code == 404
    assert client.post("/review/api/intake").status_code == 405


def test_cli_and_make_targets_are_local_and_sanitized():
    for command in (
        [".venv/bin/python", "scripts/check_intake_review_workspace.py"],
        [".venv/bin/python", "scripts/print_intake_review_workspace_summary.py"],
        ["make", "review-workspace-check"],
        ["make", "review-workspace-summary"],
    ):
        result = run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        output = result.stdout.casefold()
        assert "http://" not in output
        assert "https://" not in output
        assert "/users/" not in output

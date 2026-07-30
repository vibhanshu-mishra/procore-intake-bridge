from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import run

import pytest

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_lifecycle import IntakeReviewState
from app.models.intake_records import IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.operator_triage_queue import (
    OperatorTriageBucket,
    OperatorTriageSort,
    OperatorTriageStatus,
)
from app.services.operator_triage_queue import (
    OperatorTriageQueueError,
    build_operator_triage_filter,
    build_operator_triage_summary,
    list_operator_triage_queue,
    validate_operator_triage_response_safe,
)

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def _record(db_session, connection, *, suffix, tool="rfi", age_hours=1):
    sync_run = SyncRun(
        connection_id=connection.id,
        mode="fixture",
        status="completed",
        record_count=1,
        attachment_count=0,
    )
    db_session.add(sync_run)
    db_session.flush()
    record = IntakeRecord(
        source_type=tool,
        procore_project_id=f"fake-project-{suffix}",
        procore_item_id=f"fake-item-{suffix}",
        number=f"FAKE-{suffix}",
        title=f"Synthetic triage {suffix}",
        status="open",
        received_at=datetime.now(UTC) - timedelta(hours=age_hours),
        source_updated_at=datetime.now(UTC),
        raw_payload_json={"private_fixture": "must-not-appear"},
        attachment_count=0,
        sync_run_id=sync_run.id,
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_empty_disabled_and_unsafe_configuration_are_safe(db_session):
    summary = build_operator_triage_summary(db_session, _settings())
    assert summary.status is OperatorTriageStatus.EMPTY
    assert summary.procore_calls_made is False
    assert summary.external_calls_made is False
    assert (
        build_operator_triage_summary(db_session, _settings(triage_queue_enabled=False)).status
        is OperatorTriageStatus.DISABLED
    )
    assert (
        build_operator_triage_summary(
            db_session, _settings(triage_queue_expose_raw_payloads=True)
        ).status
        is OperatorTriageStatus.NEEDS_CONFIGURATION
    )


def test_queue_is_bounded_sorted_filtered_and_deterministic(db_session, connection):
    old = _record(db_session, connection, suffix="old", age_hours=200)
    recent = _record(db_session, connection, suffix="recent", age_hours=1)
    unknown = _record(db_session, connection, suffix="unknown", tool="other")
    db_session.add(IntakeReviewState(intake_record_id=old.id, status="needs_follow_up"))
    db_session.commit()
    settings = _settings(triage_queue_max_page_size=2)
    page = list_operator_triage_queue(
        db_session,
        build_operator_triage_filter(
            settings, page_size=999, sort=OperatorTriageSort.PRIORITY_DESC
        ),
        settings,
    )
    assert page.page_size == 2
    assert page.total_items == 3
    assert page.items[0].record_id == old.id
    assert OperatorTriageBucket.OLDER_UNREVIEWED in page.items[0].buckets
    assert page.items[0].priority_description == "Local sorting helper only."
    recent_page = list_operator_triage_queue(
        db_session,
        build_operator_triage_filter(settings, bucket="recently_received", tool="rfi"),
        settings,
    )
    assert [item.record_id for item in recent_page.items] == [recent.id]
    unknown_page = list_operator_triage_queue(
        db_session,
        build_operator_triage_filter(settings, bucket="unknown_tool"),
        settings,
    )
    assert [item.record_id for item in unknown_page.items] == [unknown.id]
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_lifecycle_filter_and_all_sorts_are_stable(db_session, connection):
    first = _record(db_session, connection, suffix="1", tool="rfi", age_hours=10)
    second = _record(db_session, connection, suffix="2", tool="submittal", age_hours=20)
    db_session.add(IntakeReviewState(intake_record_id=second.id, status="reviewed"))
    db_session.commit()
    settings = _settings()
    reviewed = list_operator_triage_queue(
        db_session,
        build_operator_triage_filter(settings, lifecycle_status="reviewed"),
        settings,
    )
    assert [item.record_id for item in reviewed.items] == [second.id]
    for sort in OperatorTriageSort:
        page = list_operator_triage_queue(
            db_session,
            build_operator_triage_filter(settings, sort=sort),
            settings,
        )
        assert sorted(item.record_id for item in page.items) == [first.id, second.id]


def test_manifest_and_missing_context_signals_expose_no_contents_or_paths(db_session, connection):
    record = _record(db_session, connection, suffix="manifest")
    db_session.add(
        AttachmentObject(
            intake_record_id=record.id,
            sync_run_id=record.sync_run_id,
            connection_id=connection.id,
            source_type="rfi",
            procore_project_id=record.procore_project_id,
            procore_item_id=record.procore_item_id,
            procore_attachment_id="fake-attachment",
            original_filename="private-name.txt",
            safe_filename="private-name.txt",
            content_type="text/plain",
            size_bytes=10,
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
    settings = _settings(intake_review_workspace_include_source_context=False)
    page = list_operator_triage_queue(db_session, build_operator_triage_filter(settings), settings)
    item = page.items[0]
    codes = {signal.code for signal in item.signals}
    assert "has_attachment_manifest" in codes
    assert "source_context_missing" in codes
    assert OperatorTriageBucket.HAS_ATTACHMENTS in item.buckets
    assert OperatorTriageBucket.MISSING_SOURCE_CONTEXT in item.buckets
    serialized = item.model_dump_json()
    assert "private-name.txt" not in serialized
    assert "/private/example" not in serialized
    assert "fake-item-manifest" not in serialized


@pytest.mark.parametrize(
    "unsafe",
    [
        {"raw_payload_json": {"fixture": True}},
        {"source_url": "hidden"},
        {"message": "https://unsafe.invalid"},
        {"message": "/Users/example/private"},
        {"message": "token=unsafe"},
    ],
)
def test_response_validator_blocks_unsafe_values(unsafe):
    with pytest.raises(OperatorTriageQueueError):
        validate_operator_triage_response_safe(unsafe)


def test_triage_routes_are_get_only_safe_and_navigable(client, db_session, connection):
    record = _record(db_session, connection, suffix="route")
    db_session.commit()
    for path in ("/review/triage", "/review/api/triage", "/review/api/triage/summary"):
        response = client.get(path)
        assert response.status_code == 200
        text = response.text.casefold()
        assert "raw_payload_json" not in text
        assert record.procore_project_id.casefold() not in text
    assert client.post("/review/api/triage").status_code == 405
    assert f"/review/intake/{record.id}" in client.get("/review/triage").text


def test_cli_and_make_targets_are_safe():
    for command in (
        [".venv/bin/python", "scripts/check_operator_triage_queue.py"],
        [".venv/bin/python", "scripts/print_operator_triage_summary.py"],
        ["make", "operator-triage-check"],
        ["make", "operator-triage-summary"],
    ):
        result = run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        output = result.stdout.casefold()
        assert "http://" not in output
        assert "https://" not in output
        assert "/users/" not in output

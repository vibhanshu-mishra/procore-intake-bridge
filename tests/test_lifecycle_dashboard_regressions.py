from datetime import UTC, datetime

import pytest
from sqlalchemy import insert, select, text

from app.config import Settings
from app.models import (
    IntakeRecord,
    IntakeReviewLifecycleEvent,
    IntakeReviewState,
    SyncRun,
)
from app.schemas.intake_lifecycle import (
    IntakeLifecycleReasonCode,
    IntakeLifecycleStatus,
)
from app.services.demo_data_experience import seed_demo_data
from app.services.intake_lifecycle import build_lifecycle_summary
from app.services.product_dashboard import build_product_dashboard_overview


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def _record(db_session, connection, suffix="legacy") -> IntakeRecord:
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
        source_type="rfi",
        procore_project_id=f"PRIVATE_PROJECT_{suffix}",
        procore_item_id=f"PRIVATE_ITEM_{suffix}",
        number=f"RFI-{suffix}",
        title=f"Synthetic lifecycle {suffix}",
        status="open",
        raw_payload_json={"private_fixture": "must-not-appear"},
        attachment_count=0,
        sync_run_id=sync_run.id,
    )
    db_session.add(record)
    db_session.flush()
    return record


def _insert_legacy_state(db_session, record_id: int, status: str = "blocked") -> None:
    timestamp = datetime.now(UTC)
    db_session.execute(
        insert(IntakeReviewState).values(
            intake_record_id=record_id,
            status=status,
            current_reason_code="J2_DEMO_FIXTURE",
            current_reason_summary_sanitized=None,
            actor_hash=None,
            actor_label_masked=None,
            event_count=1,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )


def test_legacy_blocked_row_is_normalized_and_dashboard_stays_200(
    client, db_session, connection
):
    record = _record(db_session, connection)
    _insert_legacy_state(db_session, record.id)
    db_session.execute(
        insert(IntakeReviewLifecycleEvent).values(
            intake_record_id=record.id,
            from_status="new",
            to_status="blocked",
            reason_code="J2_DEMO_FIXTURE",
            reason_summary_sanitized="Fake local lifecycle event.",
            actor_hash=None,
            actor_label_masked=None,
            request_id_hash=None,
            source="J2_DEMO_FIXTURE_legacy",
            created_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    summary = build_lifecycle_summary(db_session, _settings())
    assert summary.total_states == 1
    assert summary.counts_by_status[IntakeLifecycleStatus.NEEDS_FOLLOW_UP] == 1
    assert summary.normalized_status_count == 1
    assert summary.unknown_status_count == 0
    assert any(item.code == "legacy_status_normalized" for item in summary.findings)

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "blocked" not in response.text.casefold()
    assert "PRIVATE_PROJECT" not in response.text
    assert "must-not-appear" not in response.text

    overview = build_product_dashboard_overview(db_session, _settings())
    lifecycle = next(card for card in overview.cards if card.group == "lifecycle")
    assert lifecycle.count == 1
    assert lifecycle.metrics["needs_follow_up"] == 1
    assert overview.procore_calls_made is False
    assert overview.external_calls_made is False
    assert overview.database_writes_made is False

    history = client.get(f"/review/api/intake/{record.id}/lifecycle/history")
    assert history.status_code == 200
    assert history.json()["items"][0]["to_status"] == "needs_follow_up"
    assert history.json()["items"][0]["reason_code"] == "demo_placeholder_reason"


def test_unknown_stored_status_is_needs_review_without_raw_value(client, db_session, connection):
    record = _record(db_session, connection, suffix="unknown")
    _insert_legacy_state(db_session, record.id, status="unexpected-internal-value")
    db_session.commit()

    summary = build_lifecycle_summary(db_session, _settings())
    assert summary.total_states == 1
    assert summary.counts_by_status[IntakeLifecycleStatus.NEEDS_FOLLOW_UP] == 1
    assert summary.unknown_status_count == 1
    assert any(item.code == "unknown_status_needs_review" for item in summary.findings)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "unexpected-internal-value" not in response.text


def test_empty_partial_and_fresh_demo_dashboards_return_200(client, db_session, connection):
    assert client.get("/dashboard").status_code == 200

    _record(db_session, connection, suffix="partial")
    db_session.commit()
    assert client.get("/dashboard").status_code == 200

    report = seed_demo_data(db_session.get_bind(), _settings())
    assert report.seeded_total > 0
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "J2_DEMO_" not in response.text


def test_demo_seed_repairs_legacy_values_and_is_idempotent(db_session):
    settings = _settings()
    seed_demo_data(db_session.get_bind(), settings)
    db_session.execute(
        text(
            "UPDATE intake_review_states SET status = 'blocked', "
            "current_reason_code = 'J2_DEMO_FIXTURE' "
            "WHERE current_reason_code = 'demo_placeholder_reason'"
        )
    )
    db_session.execute(
        text(
            "UPDATE intake_review_lifecycle_events SET to_status = 'completed', "
            "reason_code = 'J2_DEMO_FIXTURE' "
            "WHERE reason_code = 'demo_placeholder_reason'"
        )
    )
    db_session.commit()
    second = seed_demo_data(db_session.get_bind(), settings)
    assert second.already_present_total > 0
    statuses = db_session.scalars(select(IntakeReviewState.status)).all()
    event_statuses = db_session.scalars(
        select(IntakeReviewLifecycleEvent.to_status)
    ).all()
    assert set(statuses) <= {status.value for status in IntakeLifecycleStatus}
    assert set(event_statuses) <= {status.value for status in IntakeLifecycleStatus}
    assert set(db_session.scalars(select(IntakeReviewState.current_reason_code)).all()) <= {
        reason.value for reason in IntakeLifecycleReasonCode
    }


def test_new_lifecycle_writes_reject_unsupported_values(db_session, connection):
    record = _record(db_session, connection, suffix="write")
    with pytest.raises(ValueError, match="Unsupported local lifecycle status"):
        db_session.add(IntakeReviewState(intake_record_id=record.id, status="blocked"))
        db_session.flush()
    db_session.rollback()

    with pytest.raises(ValueError, match="Unsupported local lifecycle status"):
        db_session.add(
            IntakeReviewLifecycleEvent(
                intake_record_id=record.id,
                from_status="new",
                to_status="blocked",
                reason_code="demo_placeholder_reason",
                reason_summary_sanitized="Synthetic local transition",
            )
        )
        db_session.flush()
    db_session.rollback()


def test_optional_lifecycle_fields_and_review_routes_are_safe(client, db_session, connection):
    record = _record(db_session, connection, suffix="optional")
    timestamp = datetime.now(UTC)
    db_session.execute(
        insert(IntakeReviewState).values(
            intake_record_id=record.id,
            status="new",
            current_reason_code=None,
            current_reason_summary_sanitized=None,
            actor_hash=None,
            actor_label_masked=None,
            event_count=0,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    db_session.commit()
    detail = client.get(f"/review/intake/{record.id}")
    history = client.get(f"/review/intake/{record.id}/lifecycle/history")
    assert detail.status_code == 200
    assert history.status_code == 200
    for body in (detail.text, history.text):
        assert "PRIVATE_PROJECT" not in body
        assert "must-not-appear" not in body
        assert "https://" not in body


def test_review_metric_labels_have_visible_spacing(client, db_session, connection):
    _record(db_session, connection, suffix="spacing")
    db_session.commit()
    body = client.get("/review").text
    assert "Statusavailable" not in body
    assert "Local records4" not in body
    assert 'class="metric-label">Status</span>' in body
    assert 'class="metric-label">Local records</span>' in body

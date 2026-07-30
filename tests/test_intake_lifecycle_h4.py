from datetime import UTC, datetime
from pathlib import Path
from subprocess import run

import pytest
from alembic import command
from sqlalchemy import inspect, select

from app.config import Settings
from app.models.intake_lifecycle import (
    IntakeReviewLifecycleEvent,
    IntakeReviewState,
)
from app.models.intake_records import IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.intake_lifecycle import (
    IntakeLifecycleReasonCode,
    IntakeLifecycleStatus,
    IntakeLifecycleTransitionRequest,
)
from app.services.intake_lifecycle import (
    ALLOWED_TRANSITIONS,
    IntakeLifecycleBlockedError,
    IntakeLifecycleError,
    apply_lifecycle_transition,
    build_lifecycle_summary,
    get_lifecycle_state,
    hash_lifecycle_actor,
    list_lifecycle_history,
    mask_lifecycle_actor,
    validate_lifecycle_response_safe,
    validate_lifecycle_transition,
)
from app.services.migration_status import get_alembic_config
from scripts.audit_routes_read_only import audit_routes

ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        enable_startup_checks=False,
        **overrides,
    )


def _record(db_session, connection) -> IntakeRecord:
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
        procore_project_id="fake-project-lifecycle",
        procore_item_id="fake-item-lifecycle",
        number="FAKE-LIFECYCLE",
        title="Synthetic lifecycle intake",
        status="open",
        received_at=datetime.now(UTC),
        source_updated_at=datetime.now(UTC),
        raw_payload_json={"fixture": True},
        attachment_count=0,
        sync_run_id=sync_run.id,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _request(
    status=IntakeLifecycleStatus.IN_REVIEW,
    reason=IntakeLifecycleReasonCode.INITIAL_REVIEW_STARTED,
    **overrides,
):
    return IntakeLifecycleTransitionRequest(
        to_status=status,
        reason_code=reason,
        actor_label="SYNTHETIC_OPERATOR_PLACEHOLDER",
        **overrides,
    )


def test_lifecycle_tables_and_reversible_migration(tmp_path):
    database = tmp_path / "lifecycle.sqlite"
    url = f"sqlite:///{database}"
    config = get_alembic_config(_settings(), url)
    command.upgrade(config, "head")
    engine = __import__("sqlalchemy").create_engine(url)
    assert {
        "intake_review_states",
        "intake_review_lifecycle_events",
    } <= set(inspect(engine).get_table_names())
    command.downgrade(config, "0001_initial_schema")
    assert "intake_review_states" not in set(inspect(engine).get_table_names())
    engine.dispose()


def test_default_state_is_created_lazily(db_session, connection):
    record = _record(db_session, connection)
    assert db_session.scalar(select(IntakeReviewState)) is None
    state = get_lifecycle_state(db_session, record.id, _settings())
    assert state.status is IntakeLifecycleStatus.NEW
    assert state.event_count == 0
    assert state.local_only is True
    assert state.procore_updated is False


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source, targets in ALLOWED_TRANSITIONS.items()
        for target in targets
    ],
)
def test_all_allowed_transitions_validate(source, target):
    validate_lifecycle_transition(
        source,
        target,
        IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON,
        _settings(),
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (IntakeLifecycleStatus.NEW, IntakeLifecycleStatus.NEW),
        (IntakeLifecycleStatus.REVIEWED, IntakeLifecycleStatus.IGNORED),
        (IntakeLifecycleStatus.IGNORED, IntakeLifecycleStatus.REVIEWED),
    ],
)
def test_invalid_transitions_fail(source, target):
    with pytest.raises(IntakeLifecycleError):
        validate_lifecycle_transition(
            source,
            target,
            IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON,
            _settings(),
        )


@pytest.mark.parametrize(
    "unsafe", ["approved", "compliance_passed", "sent_to_procore", "notified"]
)
def test_unknown_and_forbidden_statuses_fail(unsafe):
    with pytest.raises(IntakeLifecycleBlockedError):
        validate_lifecycle_transition(
            IntakeLifecycleStatus.NEW,
            unsafe,
            IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON,
            _settings(),
        )


def test_reason_required_and_free_text_blocked(db_session, connection):
    with pytest.raises(IntakeLifecycleError):
        validate_lifecycle_transition(
            IntakeLifecycleStatus.NEW,
            IntakeLifecycleStatus.IN_REVIEW,
            None,
            _settings(),
        )
    record = _record(db_session, connection)
    with pytest.raises(IntakeLifecycleBlockedError):
        apply_lifecycle_transition(
            db_session,
            record.id,
            _request(reason_summary="send to customer"),
            _settings(),
        )
    assert db_session.scalar(select(IntakeReviewLifecycleEvent)) is None


def test_transition_appends_event_masks_actor_and_is_transactional(
    db_session, connection
):
    record = _record(db_session, connection)
    result = apply_lifecycle_transition(
        db_session, record.id, _request(), _settings()
    )
    assert result.state.status is IntakeLifecycleStatus.IN_REVIEW
    assert result.state.event_count == 1
    assert result.event.from_status is IntakeLifecycleStatus.NEW
    assert result.event.actor_hash
    assert result.event.actor_label_masked.startswith("local-actor-")
    assert "SYNTHETIC_OPERATOR_PLACEHOLDER" not in result.model_dump_json()
    persisted = db_session.scalar(select(IntakeReviewState))
    event = db_session.scalar(select(IntakeReviewLifecycleEvent))
    assert persisted.status == "in_review"
    assert event.source == "local_review_workspace"


def test_history_is_bounded_and_summary_counts(db_session, connection):
    record = _record(db_session, connection)
    apply_lifecycle_transition(db_session, record.id, _request(), _settings())
    apply_lifecycle_transition(
        db_session,
        record.id,
        _request(
            IntakeLifecycleStatus.REVIEWED,
            IntakeLifecycleReasonCode.REVIEWED_NO_ACTION_NEEDED,
        ),
        _settings(),
    )
    history = list_lifecycle_history(
        db_session, record.id, 1, 500, _settings(intake_lifecycle_max_events_per_record=1)
    )
    assert history.page_size == 1
    assert history.total_items == 2
    assert history.items[0].to_status is IntakeLifecycleStatus.REVIEWED
    summary = build_lifecycle_summary(db_session, _settings())
    assert summary.counts_by_status[IntakeLifecycleStatus.REVIEWED] == 1
    assert summary.total_events == 2


def test_transition_event_limit_fails_closed(db_session, connection):
    record = _record(db_session, connection)
    settings = _settings(intake_lifecycle_max_events_per_record=1)
    apply_lifecycle_transition(db_session, record.id, _request(), settings)
    with pytest.raises(IntakeLifecycleBlockedError):
        apply_lifecycle_transition(
            db_session,
            record.id,
            _request(
                IntakeLifecycleStatus.REVIEWED,
                IntakeLifecycleReasonCode.REVIEWED_NO_ACTION_NEEDED,
            ),
            settings,
        )
    assert (
        db_session.scalar(
            select(IntakeReviewState).where(
                IntakeReviewState.intake_record_id == record.id
            )
        ).status
        == "in_review"
    )


def test_actor_helpers_and_response_safety():
    actor = "SYNTHETIC_OPERATOR_PLACEHOLDER"
    assert mask_lifecycle_actor(actor) != actor
    assert len(hash_lifecycle_actor(actor)) == 12
    for unsafe in (
        {"raw_payload_json": {"fixture": True}},
        {"source_url": "unsafe"},
        {"message": "https://unsafe.invalid"},
        {"message": "/Users/example/private"},
        {"message": "client_secret=unsafe"},
    ):
        with pytest.raises(IntakeLifecycleBlockedError):
            validate_lifecycle_response_safe(unsafe)


def test_workspace_routes_include_local_state_and_history(client, db_session, connection):
    record = _record(db_session, connection)
    detail = client.get(f"/review/api/intake/{record.id}")
    assert detail.status_code == 200
    assert detail.json()["lifecycle_status"] == "new"
    assert detail.json()["lifecycle_state"]["local_only"] is True
    transition = client.post(
        f"/review/api/intake/{record.id}/lifecycle",
        json={
            "to_status": "in_review",
            "reason_code": "initial_review_started",
            "actor_label": "SYNTHETIC_OPERATOR_PLACEHOLDER",
        },
    )
    assert transition.status_code == 200
    state = client.get(f"/review/api/intake/{record.id}/lifecycle")
    history = client.get(f"/review/api/intake/{record.id}/lifecycle/history")
    assert state.json()["status"] == "in_review"
    assert history.json()["total_items"] == 1
    html = client.get(f"/review/intake/{record.id}")
    assert f'action="/review/intake/{record.id}/lifecycle"' in html.text
    assert "local workflow state only" in html.text


def test_route_failures_are_safe(client, db_session, connection):
    record = _record(db_session, connection)
    invalid = client.post(
        f"/review/api/intake/{record.id}/lifecycle",
        json={
            "to_status": "reviewed",
            "reason_code": "reviewed_no_action_needed",
        },
    )
    assert invalid.status_code == 200
    repeated = client.post(
        f"/review/api/intake/{record.id}/lifecycle",
        json={
            "to_status": "ignored",
            "reason_code": "duplicate_or_irrelevant",
        },
    )
    assert repeated.status_code == 400
    assert client.get("/review/api/intake/99999/lifecycle").status_code == 404


def test_disabled_lifecycle_is_blocked(client, db_session, connection, monkeypatch):
    record = _record(db_session, connection)
    app_settings = _settings(intake_lifecycle_enabled=False)
    monkeypatch.setattr("app.routers.admin.get_settings", lambda: app_settings)
    response = client.post(
        f"/review/api/intake/{record.id}/lifecycle",
        json={
            "to_status": "in_review",
            "reason_code": "initial_review_started",
        },
    )
    assert response.status_code == 403


def test_route_audit_accepts_only_exact_local_lifecycle_posts():
    assert audit_routes() == []


def test_cli_and_make_checks_are_sanitized():
    commands = (
        [".venv/bin/python", "scripts/check_intake_lifecycle.py"],
        [".venv/bin/python", "scripts/print_intake_lifecycle_summary.py"],
        ["make", "intake-lifecycle-check"],
        ["make", "intake-lifecycle-summary"],
    )
    for command_line in commands:
        result = run(command_line, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        output = result.stdout.casefold()
        assert "https://" not in output
        assert "/users/" not in output
        assert "client_secret=" not in output

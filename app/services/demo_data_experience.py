import csv
import io
import json
import re
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, delete, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.database import Base
from app.models import (
    AttachmentObject,
    DMSAConnection,
    IntakeAttachment,
    IntakeRecord,
    IntakeReviewLifecycleEvent,
    IntakeReviewState,
    SyncProfile,
    SyncRun,
    WebhookEvent,
)
from app.schemas.demo_data_experience import (
    DemoDataArtifactResult,
    DemoDataDecision,
    DemoDataExperienceReport,
    DemoDataFinding,
    DemoDataInventoryItem,
    DemoDataRecordPlan,
    DemoDatasetKind,
    DemoDataStatus,
    DemoResetAction,
    DemoResetReport,
    DemoSeedAction,
    DemoSeedReport,
)
from app.schemas.intake_lifecycle import IntakeLifecycleReasonCode, IntakeLifecycleStatus
from app.services.intake_lifecycle import normalize_legacy_lifecycle_data


class DemoDataExperienceError(ValueError):
    pass


class DemoDataExperienceBlockedError(DemoDataExperienceError):
    pass


DEMO_MARKER = "J2_DEMO_"
RESET_CONFIRMATION = "RESET DEMO DATA"
ARTIFACT_FILES = (
    "demo-data-report.json",
    "demo-data-report.md",
    "demo-seed-plan.md",
    "demo-reset-plan.md",
    "demo-data-inventory.csv",
    "manifest.json",
)
SAFE_ROOTS = {
    "demo-data-output",
    "demo-seed-output",
    "demo-reset-output",
    "demo-db-output",
}
UNSAFE_VALUE = re.compile(
    r"(?i)(?:https?|s3|gs|postgres(?:ql)?)://|(?:/Users/|/home/|/private/|[A-Z]:\\)|"
    r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|(?:bearer|token|password|secret)\s*[:=]\s*\S+|"
    r"\b(?:arn:aws|subscription[_ -]?id|signed[_ -]?url|private[_ -]?key)\b"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:production|release|pilot|launch) approved\b|"
    r"\b(?:production|release|pilot)[- ]ready\b|"
    r"\b(?:soc ?2|iso ?27001|gdpr|ccpa|hipaa|slsa|sbom) (?:certified|compliant)\b"
)

_PLAN_COUNTS = {
    DemoDatasetKind.INTAKE_RECORDS: 4,
    DemoDatasetKind.ATTACHMENT_MANIFESTS: 3,
    DemoDatasetKind.LIFECYCLE_STATES: 4,
    DemoDatasetKind.LIFECYCLE_EVENTS: 3,
    DemoDatasetKind.TRIAGE_SIGNALS: 3,
    DemoDatasetKind.DASHBOARD_COUNTS: 1,
    DemoDatasetKind.EXPORT_SUMMARIES: 1,
    DemoDatasetKind.EVENT_QUEUE_FIXTURES: 2,
    DemoDatasetKind.SYNC_RUN_FIXTURES: 1,
}


def sanitize_demo_data_value(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if UNSAFE_VALUE.search(text) or UNSAFE_CLAIM.search(text):
        return "[redacted]"
    return text[:500]


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _settings_blockers(settings: Settings) -> list[str]:
    required_true = (
        "demo_data_experience_enabled",
        "demo_data_require_fake_only",
        "demo_data_require_local_sqlite_only",
        "demo_data_require_idempotent_seed",
        "demo_data_require_reset_confirmation",
        "demo_data_fail_closed",
    )
    required_false = (
        "demo_data_allow_private_workspace_reset",
        "demo_data_allow_sandbox_reset",
        "demo_data_allow_pilot_reset",
        "demo_data_allow_hosted_reset",
        "demo_data_allow_real_identities",
        "demo_data_allow_real_domains",
        "demo_data_allow_real_urls",
        "demo_data_allow_report_contents",
        "demo_data_allow_private_paths",
    )
    blockers = [name for name in required_true if not _setting(settings, name, True)]
    blockers.extend(name for name in required_false if _setting(settings, name, False))
    if _setting(settings, "demo_data_reset_confirmation", RESET_CONFIRMATION) != RESET_CONFIRMATION:
        blockers.append("demo_data_reset_confirmation")
    maximum = _setting(settings, "demo_data_max_records", 50)
    if maximum < sum(_PLAN_COUNTS.values()) or maximum > 50:
        blockers.append("demo_data_max_records")
    return blockers


def _require_safe_settings(settings: Settings) -> None:
    blockers = _settings_blockers(settings)
    if blockers:
        raise DemoDataExperienceBlockedError(
            "Demo data operation blocked by fail-closed settings: " + ", ".join(blockers)
        )


def build_demo_dataset_plan(settings: Settings) -> list[DemoDataRecordPlan]:
    _require_safe_settings(settings)
    descriptions = {
        DemoDatasetKind.INTAKE_RECORDS: "Fake RFI and submittal intake rows.",
        DemoDatasetKind.ATTACHMENT_MANIFESTS: "Metadata-only fake attachment manifests.",
        DemoDatasetKind.LIFECYCLE_STATES: "Review workspace lifecycle states.",
        DemoDatasetKind.LIFECYCLE_EVENTS: "Sanitized lifecycle transitions.",
        DemoDatasetKind.TRIAGE_SIGNALS: "Derived overdue and review-ready signals.",
        DemoDatasetKind.DASHBOARD_COUNTS: "Counts derived from demo-marked rows.",
        DemoDatasetKind.EXPORT_SUMMARIES: "Summary inputs derived from demo-marked rows.",
        DemoDatasetKind.EVENT_QUEUE_FIXTURES: "Fake local event queue rows.",
        DemoDatasetKind.SYNC_RUN_FIXTURES: "One completed local fixture sync run.",
    }
    return [
        DemoDataRecordPlan(
            dataset_kind=kind,
            record_count=count,
            description=descriptions[kind],
        )
        for kind, count in _PLAN_COUNTS.items()
    ]


def build_demo_seed_plan(settings: Settings) -> DemoSeedReport:
    actions = build_demo_dataset_plan(settings)
    return DemoSeedReport(
        status=DemoDataStatus.READY,
        planned_total=sum(item.record_count for item in actions),
        actions=actions,
    )


def build_demo_reset_plan(settings: Settings) -> DemoResetReport:
    actions = [
        item.model_copy(update={"seed_action": DemoSeedAction.VERIFY})
        for item in build_demo_dataset_plan(settings)
    ]
    return DemoResetReport(
        status=DemoDataStatus.READY,
        planned_total=sum(item.record_count for item in actions),
        actions=actions,
        findings=[
            DemoDataFinding(
                code="confirmation_required",
                message="Reset requires the exact Demo Mode confirmation phrase.",
            )
        ],
    )


def _engine(value: Session | Engine) -> Engine:
    bind = value.get_bind() if isinstance(value, Session) else value
    if not isinstance(bind, Engine):
        raise DemoDataExperienceBlockedError("A SQLAlchemy Session or Engine is required.")
    if bind.dialect.name != "sqlite":
        raise DemoDataExperienceBlockedError("Demo data operations require local SQLite.")
    database = inspect(bind).engine.url.database
    if database and database != ":memory:":
        path = Path(database)
        if path.is_absolute() and not (
            path.as_posix().startswith("/tmp/")
            or "pytest-" in path.as_posix()
            or path.name in {"procore_intake_bridge.db", "demo.db"}
        ):
            raise DemoDataExperienceBlockedError("SQLite path is outside local Demo Mode scope.")
    return bind


@contextmanager
def _session(value: Session | Engine):
    engine = _engine(value)
    if isinstance(value, Session):
        yield value
        return
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session


def _ensure_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def _get_or_create(session: Session, model, predicate, values: dict[str, Any]):
    existing = session.scalar(select(model).where(predicate))
    if existing is not None:
        return existing, False
    instance = model(**values)
    session.add(instance)
    session.flush()
    return instance, True


def seed_demo_data(session_or_engine: Session | Engine, settings: Settings) -> DemoSeedReport:
    _require_safe_settings(settings)
    engine = _engine(session_or_engine)
    _ensure_tables(engine)
    created = 0
    fixed_time = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    with _session(session_or_engine) as session:
        connection, was_created = _get_or_create(
            session,
            DMSAConnection,
            DMSAConnection.procore_company_id == f"{DEMO_MARKER}COMPANY",
            {
                "name": f"{DEMO_MARKER}LOCAL_FIXTURE",
                "procore_company_id": f"{DEMO_MARKER}COMPANY",
                "permitted_project_ids": [f"{DEMO_MARKER}PROJECT"],
                "enabled_tools": ["rfis", "submittals"],
                "secret_name": f"{DEMO_MARKER}NO_CREDENTIAL",
            },
        )
        created += was_created
        profile, was_created = _get_or_create(
            session,
            SyncProfile,
            (SyncProfile.connection_id == connection.id)
            & (SyncProfile.procore_project_id == f"{DEMO_MARKER}PROJECT"),
            {
                "connection_id": connection.id,
                "procore_project_id": f"{DEMO_MARKER}PROJECT",
                "name": f"{DEMO_MARKER}PROFILE",
                "mode": "mock",
            },
        )
        created += was_created
        run, was_created = _get_or_create(
            session,
            SyncRun,
            (SyncRun.connection_id == connection.id) & (SyncRun.mode == "j2_demo_fixture"),
            {
                "connection_id": connection.id,
                "mode": "j2_demo_fixture",
                "status": "completed",
                "record_count": 4,
                "attachment_count": 3,
                "started_at": fixed_time,
                "completed_at": fixed_time,
            },
        )
        created += was_created
        records = (
            ("rfi", "001", "Coordinate ceiling access", "open", date(2026, 1, 10), 1, "new"),
            ("rfi", "002", "Confirm finish selection", "open", date(2026, 1, 20), 1, "in_review"),
            (
                "submittal",
                "003",
                "Review door hardware set",
                "pending",
                date(2026, 1, 12),
                1,
                IntakeLifecycleStatus.NEEDS_FOLLOW_UP.value,
            ),
            (
                "submittal",
                "004",
                "Review lighting schedule",
                "closed",
                None,
                0,
                IntakeLifecycleStatus.REVIEWED.value,
            ),
        )
        seeded_records: list[IntakeRecord] = []
        for source, suffix, title, status, due, attachments, review_status in records:
            marker_id = f"{DEMO_MARKER}{source.upper()}_{suffix}"
            record, was_created = _get_or_create(
                session,
                IntakeRecord,
                (IntakeRecord.source_type == source)
                & (IntakeRecord.procore_project_id == f"{DEMO_MARKER}PROJECT")
                & (IntakeRecord.procore_item_id == marker_id),
                {
                    "source_type": source,
                    "procore_project_id": f"{DEMO_MARKER}PROJECT",
                    "procore_item_id": marker_id,
                    "number": f"DEMO-{suffix}",
                    "title": f"{DEMO_MARKER}{title}",
                    "status": status,
                    "due_date": due,
                    "received_at": fixed_time,
                    "source_updated_at": fixed_time,
                    "raw_payload_json": {"fixture": f"{DEMO_MARKER}FAKE_ONLY"},
                    "attachment_count": attachments,
                    "sync_run_id": run.id,
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
            )
            created += was_created
            seeded_records.append(record)
            _, state_created = _get_or_create(
                session,
                IntakeReviewState,
                IntakeReviewState.intake_record_id == record.id,
                {
                    "intake_record_id": record.id,
                    "status": review_status,
                    "current_reason_code": IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON.value,
                    "current_reason_summary_sanitized": "Fake local review state.",
                    "actor_label_masked": f"{DEMO_MARKER}ACTOR",
                    "event_count": 1 if review_status != "new" else 0,
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
            )
            created += state_created
        for index, record in enumerate(seeded_records[:3], start=1):
            _, event_created = _get_or_create(
                session,
                IntakeReviewLifecycleEvent,
                (IntakeReviewLifecycleEvent.intake_record_id == record.id)
                & (IntakeReviewLifecycleEvent.source == f"{DEMO_MARKER}FIXTURE_{index}"),
                {
                    "intake_record_id": record.id,
                    "from_status": "new",
                    "to_status": (
                        IntakeLifecycleStatus.IN_REVIEW.value,
                        IntakeLifecycleStatus.NEEDS_FOLLOW_UP.value,
                        IntakeLifecycleStatus.REVIEWED.value,
                    )[index - 1],
                    "reason_code": IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON.value,
                    "reason_summary_sanitized": "Fake local lifecycle event.",
                    "actor_label_masked": f"{DEMO_MARKER}ACTOR",
                    "source": f"{DEMO_MARKER}FIXTURE_{index}",
                    "created_at": fixed_time,
                },
            )
            created += event_created
        normalize_legacy_lifecycle_data(
            session, [record.id for record in seeded_records]
        )
        for index, record in enumerate(seeded_records[:3], start=1):
            attachment_id = f"{DEMO_MARKER}ATTACHMENT_{index}"
            _, attachment_created = _get_or_create(
                session,
                IntakeAttachment,
                IntakeAttachment.procore_attachment_id == attachment_id,
                {
                    "intake_record_id": record.id,
                    "procore_attachment_id": attachment_id,
                    "filename": f"demo-placeholder-{index}.txt",
                    "content_type": "text/plain",
                    "source_url_redacted": None,
                    "created_at": fixed_time,
                },
            )
            created += attachment_created
            _, object_created = _get_or_create(
                session,
                AttachmentObject,
                AttachmentObject.procore_attachment_id == attachment_id,
                {
                    "intake_record_id": record.id,
                    "sync_run_id": run.id,
                    "connection_id": connection.id,
                    "sync_profile_id": profile.id,
                    "source_type": record.source_type,
                    "procore_project_id": f"{DEMO_MARKER}PROJECT",
                    "procore_item_id": record.procore_item_id,
                    "procore_attachment_id": attachment_id,
                    "original_filename": f"demo-placeholder-{index}.txt",
                    "safe_filename": f"demo-placeholder-{index}.txt",
                    "content_type": "text/plain",
                    "size_bytes": 0,
                    "source_url_present": False,
                    "storage_backend": "local_demo_metadata_only",
                    "storage_key": f"{DEMO_MARKER}NO_OBJECT_{index}",
                    "storage_path": f"demo-local/{DEMO_MARKER}NO_FILE_{index}",
                    "download_status": "planned",
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
            )
            created += object_created
        for index, record in enumerate(seeded_records[:2], start=1):
            event_id = f"{DEMO_MARKER}EVENT_{index}"
            _, event_created = _get_or_create(
                session,
                WebhookEvent,
                WebhookEvent.event_id == event_id,
                {
                    "connection_id": connection.id,
                    "sync_profile_id": profile.id,
                    "source": "j2_demo_fixture",
                    "event_id": event_id,
                    "event_type": f"{DEMO_MARKER}FIXTURE_EVENT",
                    "resource_type": record.source_type,
                    "action": "fixture",
                    "procore_company_id": f"{DEMO_MARKER}COMPANY",
                    "procore_project_id": f"{DEMO_MARKER}PROJECT",
                    "procore_item_id": record.procore_item_id,
                    "payload_json": {"fixture": f"{DEMO_MARKER}FAKE_ONLY"},
                    "normalized_json": {"fixture": f"{DEMO_MARKER}FAKE_ONLY"},
                    "signature_status": "not_applicable_fixture",
                    "processing_status": "queued",
                    "received_at": fixed_time,
                    "available_at": fixed_time,
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                },
            )
            created += event_created
        session.commit()
    plan = build_demo_seed_plan(settings)
    actual_seed_rows = 4 + 4 + 3 + 3 + 2 + 1
    return plan.model_copy(
        update={
            "seeded_total": actual_seed_rows,
            "already_present_total": max(actual_seed_rows - created, 0),
        }
    )


def _counts(session: Session) -> dict[DemoDatasetKind, int]:
    marker = f"{DEMO_MARKER}%"
    intake_ids = select(IntakeRecord.id).where(IntakeRecord.procore_item_id.like(marker))
    return {
        DemoDatasetKind.INTAKE_RECORDS: session.scalar(
            select(func.count())
            .select_from(IntakeRecord)
            .where(IntakeRecord.procore_item_id.like(marker))
        )
        or 0,
        DemoDatasetKind.ATTACHMENT_MANIFESTS: session.scalar(
            select(func.count())
            .select_from(AttachmentObject)
            .where(AttachmentObject.procore_attachment_id.like(marker))
        )
        or 0,
        DemoDatasetKind.LIFECYCLE_STATES: session.scalar(
            select(func.count())
            .select_from(IntakeReviewState)
            .where(IntakeReviewState.intake_record_id.in_(intake_ids))
        )
        or 0,
        DemoDatasetKind.LIFECYCLE_EVENTS: session.scalar(
            select(func.count())
            .select_from(IntakeReviewLifecycleEvent)
            .where(IntakeReviewLifecycleEvent.source.like(marker))
        )
        or 0,
        DemoDatasetKind.TRIAGE_SIGNALS: session.scalar(
            select(func.count())
            .select_from(IntakeRecord)
            .where(IntakeRecord.procore_item_id.like(marker), IntakeRecord.status != "closed")
        )
        or 0,
        DemoDatasetKind.DASHBOARD_COUNTS: 1,
        DemoDatasetKind.EXPORT_SUMMARIES: 1,
        DemoDatasetKind.EVENT_QUEUE_FIXTURES: session.scalar(
            select(func.count()).select_from(WebhookEvent).where(WebhookEvent.event_id.like(marker))
        )
        or 0,
        DemoDatasetKind.SYNC_RUN_FIXTURES: session.scalar(
            select(func.count()).select_from(SyncRun).where(SyncRun.mode == "j2_demo_fixture")
        )
        or 0,
    }


def build_demo_data_inventory(
    session_or_engine: Session | Engine, settings: Settings
) -> list[DemoDataInventoryItem]:
    _require_safe_settings(settings)
    engine = _engine(session_or_engine)
    _ensure_tables(engine)
    with _session(session_or_engine) as session:
        counts = _counts(session)
    return [
        DemoDataInventoryItem(dataset_kind=kind, record_count=count)
        for kind, count in counts.items()
    ]


def reset_demo_data(
    session_or_engine: Session | Engine, settings: Settings, confirmation: str
) -> DemoResetReport:
    _require_safe_settings(settings)
    expected = _setting(settings, "demo_data_reset_confirmation", RESET_CONFIRMATION)
    if confirmation != expected:
        raise DemoDataExperienceBlockedError("Exact Demo Mode reset confirmation is required.")
    engine = _engine(session_or_engine)
    _ensure_tables(engine)
    with _session(session_or_engine) as session:
        before = _counts(session)
        marker = f"{DEMO_MARKER}%"
        intake_ids = select(IntakeRecord.id).where(IntakeRecord.procore_item_id.like(marker))
        connection_ids = select(DMSAConnection.id).where(
            DMSAConnection.procore_company_id.like(marker)
        )
        session.execute(
            delete(AttachmentObject).where(AttachmentObject.procore_attachment_id.like(marker))
        )
        session.execute(
            delete(IntakeAttachment).where(IntakeAttachment.procore_attachment_id.like(marker))
        )
        session.execute(
            delete(IntakeReviewLifecycleEvent).where(
                IntakeReviewLifecycleEvent.intake_record_id.in_(intake_ids)
            )
        )
        session.execute(
            delete(IntakeReviewState).where(IntakeReviewState.intake_record_id.in_(intake_ids))
        )
        session.execute(delete(WebhookEvent).where(WebhookEvent.event_id.like(marker)))
        session.execute(delete(IntakeRecord).where(IntakeRecord.procore_item_id.like(marker)))
        session.execute(
            delete(SyncRun).where(
                SyncRun.mode == "j2_demo_fixture",
                ~SyncRun.id.in_(select(IntakeRecord.sync_run_id)),
            )
        )
        session.execute(
            delete(SyncProfile).where(
                SyncProfile.connection_id.in_(connection_ids),
                SyncProfile.procore_project_id.like(marker),
            )
        )
        session.execute(
            delete(DMSAConnection).where(
                DMSAConnection.procore_company_id.like(marker),
                ~DMSAConnection.id.in_(select(SyncRun.connection_id)),
                ~DMSAConnection.id.in_(select(SyncProfile.connection_id)),
            )
        )
        session.commit()
        after = _counts(session)
    removed = sum(
        before[kind] - after[kind]
        for kind in (
            DemoDatasetKind.INTAKE_RECORDS,
            DemoDatasetKind.ATTACHMENT_MANIFESTS,
            DemoDatasetKind.LIFECYCLE_STATES,
            DemoDatasetKind.LIFECYCLE_EVENTS,
            DemoDatasetKind.EVENT_QUEUE_FIXTURES,
            DemoDatasetKind.SYNC_RUN_FIXTURES,
        )
    )
    return DemoResetReport(
        status=DemoDataStatus.READY,
        planned_total=removed,
        removed_total=removed,
        actions=build_demo_reset_plan(settings).actions,
    )


def build_demo_data_experience_report(settings: Settings) -> DemoDataExperienceReport:
    blockers = _settings_blockers(settings)
    plan = [] if blockers else build_demo_dataset_plan(settings)
    report = DemoDataExperienceReport(
        status=DemoDataStatus.BLOCKED if blockers else DemoDataStatus.READY,
        decision=DemoDataDecision.BLOCKED if blockers else DemoDataDecision.READY,
        fake_records_planned_total=sum(item.record_count for item in plan),
        reset_items_planned_total=sum(item.record_count for item in plan),
        blockers=[f"Fail-closed setting requires correction: {name}." for name in blockers],
        warnings=[
            "Reset is limited to records carrying the deterministic J2 Demo Mode marker.",
            "Demo readiness does not imply production, pilot, or release approval.",
        ],
        dataset_plan=plan,
        recommended_next_steps=[
            "Print the seed plan before writing local fake data.",
            "Print the reset plan before using the confirmation-gated reset.",
        ],
    )
    validate_demo_data_report_safe(report)
    return report


def validate_demo_data_report_safe(report: BaseModel | str | Any) -> None:
    if isinstance(report, BaseModel):
        data = report.model_dump(mode="json")
        for field in (
            "external_call_attempted",
            "procore_call_attempted",
            "cloud_call_attempted",
            "external_db_connection_attempted",
            "sandbox_data_touched",
            "pilot_data_touched",
            "hosted_data_touched",
            "private_workspace_touched",
            "customer_data_touched",
            "private_report_contents_exposed",
            "secrets_exposed",
            "urls_exposed",
            "private_paths_exposed",
            "ids_exposed",
            "real_domains_exposed",
            "production_approval_claimed",
            "release_approval_claimed",
            "pilot_approval_claimed",
        ):
            if data.get(field) is True:
                raise DemoDataExperienceBlockedError(f"Unsafe report flag: {field}.")
        text = json.dumps(data)
    else:
        text = str(report)
    if UNSAFE_VALUE.search(text) or UNSAFE_CLAIM.search(text):
        raise DemoDataExperienceBlockedError("Unsafe value in Demo Mode output.")


def render_demo_data_report_markdown(report: DemoDataExperienceReport) -> str:
    lines = [
        "# Local Demo Data Experience",
        "",
        f"- Status: `{report.status.value}`",
        f"- Decision: `{report.decision.value}`",
        f"- Fake records planned: {report.fake_records_planned_total}",
        "- Scope: local SQLite and deterministic fake data only",
        "",
        "## Dataset plan",
        "",
    ]
    lines.extend(
        f"- `{item.dataset_kind.value}`: {item.record_count} — {item.description}"
        for item in report.dataset_plan
    )
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {sanitize_demo_data_value(item)}" for item in report.warnings)
    text = "\n".join(lines) + "\n"
    validate_demo_data_report_safe(text)
    return text


def render_demo_seed_plan_markdown(report: DemoSeedReport | DemoDataExperienceReport) -> str:
    actions = report.actions if isinstance(report, DemoSeedReport) else report.dataset_plan
    lines = ["# Demo Seed Plan", "", "This plan is non-destructive and fake-data-only.", ""]
    lines.extend(
        f"- `{item.dataset_kind.value}`: seed {item.record_count} deterministic fixture items."
        for item in actions
    )
    text = "\n".join(lines) + "\n"
    validate_demo_data_report_safe(text)
    return text


def render_demo_reset_plan_markdown(report: DemoResetReport | DemoDataExperienceReport) -> str:
    actions = report.actions if isinstance(report, DemoResetReport) else report.dataset_plan
    lines = [
        "# Demo Reset Plan",
        "",
        "Reset requires exact confirmation and removes only J2 demo-marked local records.",
        (
            "Unmarked, private workspace, sandbox, pilot, hosted, cloud, and customer "
            "data remain untouched."
        ),
        "",
    ]
    lines.extend(
        f"- `{item.dataset_kind.value}`: `{DemoResetAction.REMOVE_DEMO_MARKED.value}`."
        for item in actions
    )
    text = "\n".join(lines) + "\n"
    validate_demo_data_report_safe(text)
    return text


def _csv_safe(value: Any) -> str:
    text = sanitize_demo_data_value(value)
    return f"'{text}" if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_demo_data_inventory_csv(
    report_or_inventory: DemoDataExperienceReport | list[DemoDataInventoryItem],
) -> str:
    inventory = (
        report_or_inventory.inventory
        if isinstance(report_or_inventory, DemoDataExperienceReport)
        else report_or_inventory
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("dataset_kind", "marker", "record_count", "fake_only", "local_only"))
    for item in inventory:
        writer.writerow(
            tuple(
                _csv_safe(value)
                for value in (
                    item.dataset_kind.value,
                    item.marker,
                    item.record_count,
                    item.fake_only,
                    item.local_only,
                )
            )
        )
    text = output.getvalue()
    validate_demo_data_report_safe(text)
    return text


def _safe_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    temporary = root.is_absolute() and (
        (root.parent == Path("/tmp") and root.name.startswith("procore-intake-bridge-demo-data-"))
        or "pytest-" in root.as_posix()
    )
    if (
        ".." in root.parts
        or (root.is_absolute() and not temporary)
        or (not temporary and root.parts[:1] not in {(value,) for value in SAFE_ROOTS})
    ):
        raise DemoDataExperienceBlockedError("Unsafe demo-data output root.")
    return root


def write_demo_data_experience_artifacts(
    report: DemoDataExperienceReport, output_root: str | Path
) -> DemoDataArtifactResult:
    root = _safe_output_root(output_root)
    seed_report = DemoSeedReport(
        status=report.status,
        planned_total=report.fake_records_planned_total,
        seeded_total=report.fake_records_seeded_total,
        actions=report.dataset_plan,
    )
    reset_report = DemoResetReport(
        status=report.status,
        planned_total=report.reset_items_planned_total,
        removed_total=report.reset_items_removed_total,
        actions=report.dataset_plan,
    )
    artifacts = {
        "demo-data-report.json": report.model_dump_json(indent=2),
        "demo-data-report.md": render_demo_data_report_markdown(report),
        "demo-seed-plan.md": render_demo_seed_plan_markdown(seed_report),
        "demo-reset-plan.md": render_demo_reset_plan_markdown(reset_report),
        "demo-data-inventory.csv": render_demo_data_inventory_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {"files": sorted(artifacts), "sanitized": True, "external_operations": False},
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in artifacts.items():
        validate_demo_data_report_safe(content)
        (root / filename).write_text(content)
    return DemoDataArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=sorted(artifacts),
    )

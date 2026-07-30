from datetime import UTC, datetime
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_lifecycle import (
    IntakeReviewLifecycleEvent,
    IntakeReviewState,
)
from app.models.intake_records import IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.operator_export_pack import (
    OperatorExportFormat,
    OperatorExportStatus,
)
from app.services.operator_export_pack import (
    OperatorExportPackBlockedError,
    build_operator_export_combined_packet,
    build_operator_export_filter,
    build_operator_export_metadata,
    render_operator_export_csv_sections,
    render_operator_export_json,
    render_operator_export_markdown,
    validate_operator_export_safe,
    write_operator_export_artifacts,
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


def _record(db_session, connection, *, suffix, title=None):
    run_row = SyncRun(
        connection_id=connection.id,
        mode="fixture",
        status="completed",
        record_count=1,
        attachment_count=1,
    )
    db_session.add(run_row)
    db_session.flush()
    record = IntakeRecord(
        source_type="rfi" if suffix != "2" else "submittal",
        procore_project_id=f"fake-project-{suffix}",
        procore_item_id=f"fake-item-{suffix}",
        number=f"FAKE-{suffix}",
        title=title or f"Synthetic export record {suffix}",
        status="open",
        received_at=datetime.now(UTC),
        source_updated_at=datetime.now(UTC),
        raw_payload_json={"private_fixture": "must-not-appear"},
        attachment_count=1,
        sync_run_id=run_row.id,
    )
    db_session.add(record)
    db_session.flush()
    return record


def _seed(db_session, connection):
    first = _record(db_session, connection, suffix="1", title="=SUM(A1:A2)")
    second = _record(db_session, connection, suffix="2")
    third = _record(db_session, connection, suffix="3")
    db_session.add(
        AttachmentObject(
            intake_record_id=first.id,
            sync_run_id=first.sync_run_id,
            connection_id=connection.id,
            source_type="rfi",
            procore_project_id=first.procore_project_id,
            procore_item_id=first.procore_item_id,
            procore_attachment_id="fake-attachment-1",
            original_filename="private-live-name.pdf",
            safe_filename="private-live-name.pdf",
            content_type="application/pdf",
            size_bytes=100,
            source_url_present=True,
            source_url_hash="a" * 64,
            storage_backend="local",
            storage_key="private-object-key",
            storage_path="/private/example",
            checksum_sha256="b" * 64,
            download_status="downloaded",
        )
    )
    state = IntakeReviewState(
        intake_record_id=first.id,
        status="in_review",
        current_reason_code="initial_review_started",
        event_count=1,
    )
    db_session.add(state)
    db_session.add(
        IntakeReviewLifecycleEvent(
            intake_record_id=first.id,
            from_status="new",
            to_status="in_review",
            reason_code="initial_review_started",
            reason_summary_sanitized="Synthetic local transition",
            actor_hash="c" * 64,
            actor_label_masked="local-actor-placeholder",
            request_id_hash="d" * 64,
        )
    )
    db_session.commit()
    return first, second, third


def test_empty_packet_and_metadata_are_safe(db_session):
    settings = _settings()
    filters = build_operator_export_filter(settings)
    packet = build_operator_export_combined_packet(db_session, filters, settings)
    assert packet.metadata.status is OperatorExportStatus.AVAILABLE
    assert packet.intake.status is OperatorExportStatus.EMPTY
    assert packet.lifecycle.local_labels_only is True
    assert packet.triage.description == "Deterministic local sorting summary only."
    assert packet.attachments.contents_available is False
    assert packet.events.status is OperatorExportStatus.EMPTY
    metadata = build_operator_export_metadata(db_session, settings)
    assert metadata.raw_payloads_exposed is False
    assert metadata.compliance_or_approval_claimed is False
    validate_operator_export_safe(packet)


def test_combined_packet_is_bounded_sanitized_and_complete(db_session, connection):
    first, _, _ = _seed(db_session, connection)
    settings = _settings(export_pack_max_records=2)
    filters = build_operator_export_filter(settings, max_records=999)
    packet = build_operator_export_combined_packet(db_session, filters, settings)
    assert packet.intake.total_records == 3
    assert packet.intake.exported_records == 2
    assert packet.lifecycle.counts_by_status["in_review"] == 1
    assert packet.lifecycle.total_events == 1
    assert packet.triage.total_records == 3
    assert packet.attachments.records_with_manifests == 1
    assert packet.attachments.metadata_only is True
    assert packet.events.total_events == 1
    assert packet.events.exported_events == 1
    assert packet.events.events[0]["transition"] == "new->in_review"
    serialized = packet.model_dump_json()
    for unsafe in (
        first.procore_item_id,
        "private-live-name.pdf",
        "private-object-key",
        "/private/example",
        "actor_hash",
        "raw_payload_json",
        "source_url_hash",
    ):
        assert unsafe not in serialized
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_json_markdown_and_csv_are_safe_and_csv_neutralizes_formulas(db_session, connection):
    _seed(db_session, connection)
    settings = _settings()
    packet = build_operator_export_combined_packet(
        db_session, build_operator_export_filter(settings), settings
    )
    rendered_json = render_operator_export_json(packet)
    rendered_markdown = render_operator_export_markdown(packet)
    rendered_csv = render_operator_export_csv_sections(packet)
    assert '"raw_payloads_exposed": false' in rendered_json
    assert "not an official external report" in rendered_markdown
    assert "'=SUM(A1:A2)" in rendered_csv["combined.operator-export.csv"]
    for output in (rendered_json, rendered_markdown, *rendered_csv.values()):
        validate_operator_export_safe(output)


def test_disabled_and_unsafe_settings_fail_closed(db_session):
    disabled = _settings(export_pack_enabled=False)
    packet = build_operator_export_combined_packet(
        db_session, build_operator_export_filter(disabled), disabled
    )
    assert packet.metadata.status is OperatorExportStatus.DISABLED
    unsafe = _settings(export_pack_expose_contents=True)
    packet = build_operator_export_combined_packet(
        db_session, build_operator_export_filter(unsafe), unsafe
    )
    assert packet.metadata.status is OperatorExportStatus.NEEDS_CONFIGURATION


@pytest.mark.parametrize(
    "unsafe",
    [
        {"raw_payload_json": {"fixture": True}},
        {"source_url": "hidden"},
        {"signed_url": "hidden"},
        {"storage_key": "hidden"},
        {"original_filename": "hidden"},
        {"message": "https://unsafe.invalid/value"},
        {"message": "/Users/example/private"},
        {"message": "client_secret=unsafe"},
        {"message": "official customer report"},
        {"message": "compliance certificate"},
        {"message": "approval granted"},
    ],
)
def test_safety_validator_blocks_unsafe_content(unsafe):
    with pytest.raises(OperatorExportPackBlockedError):
        validate_operator_export_safe(unsafe)


def test_output_traversal_and_unapproved_roots_are_blocked(db_session):
    settings = _settings()
    packet = build_operator_export_combined_packet(
        db_session, build_operator_export_filter(settings), settings
    )
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved-export")):
        with pytest.raises(OperatorExportPackBlockedError):
            write_operator_export_artifacts(packet, path, [OperatorExportFormat.JSON])


def test_temp_artifacts_include_json_markdown_and_csv(db_session, connection):
    _seed(db_session, connection)
    settings = _settings()
    filters = build_operator_export_filter(settings)
    packet = build_operator_export_combined_packet(db_session, filters, settings)
    with TemporaryDirectory(
        prefix="procore-intake-bridge-operator-export-", dir="/tmp"
    ) as temporary:
        result = write_operator_export_artifacts(packet, Path(temporary), filters.formats)
        assert result.status is OperatorExportStatus.WRITTEN
        assert result.output_directory == Path(temporary).name
        assert set(result.files) == {
            "combined.operator-export.json",
            "combined.operator-export.md",
            "combined.operator-export.csv",
        }
        for name in result.files:
            content = (Path(temporary) / name).read_text(encoding="utf-8")
            assert "private-live-name" not in content
            validate_operator_export_safe(content)


def test_builders_do_not_open_attachment_files(monkeypatch, db_session, connection):
    _seed(db_session, connection)

    def blocked_open(*args, **kwargs):
        raise AssertionError("attachment file access is outside H7")

    monkeypatch.setattr("builtins.open", blocked_open)
    settings = _settings()
    packet = build_operator_export_combined_packet(
        db_session, build_operator_export_filter(settings), settings
    )
    assert packet.attachments.metadata_only is True
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_no_export_route_exists_and_route_audit_passes():
    assert not audit_routes()
    assert not any(
        route.path.startswith("/review") and "export" in route.path.casefold()
        for route in application_routes()
    )


def test_docs_makefile_and_ignore_contracts_are_registered():
    required = (
        "README.md",
        "QUICKSTART.md",
        "docs/operator-export-pack.md",
        "docs/command-reference.md",
        "mkdocs.yml",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in required)
    lowered = combined.casefold()
    for phrase in (
        "operator export",
        "local sanitized",
        "no public export route",
        "operator-export-check",
        "operator-export-summary",
    ):
        assert phrase in lowered
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "quality: operator-export-check operator-export-summary" in makefile
    assert "quality: operator-export-artifact-check" not in makefile
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (
        "operator-export-output/",
        "*.operator-export.json",
        "*.operator-export.md",
        "*.operator-export.csv",
    ):
        assert pattern in ignore


def test_cli_and_make_targets_are_safe():
    commands = (
        [".venv/bin/python", "scripts/check_operator_export_pack.py"],
        [".venv/bin/python", "scripts/print_operator_export_summary.py"],
        [
            ".venv/bin/python",
            "scripts/generate_operator_export_pack.py",
            "--temporary",
        ],
        ["make", "operator-export-check"],
        ["make", "operator-export-summary"],
        ["make", "operator-export-artifact-check"],
    )
    for command in commands:
        result = run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        output = result.stdout.casefold()
        assert "http://" not in output
        assert "https://" not in output
        assert "/users/" not in output
        assert "/private/" not in output

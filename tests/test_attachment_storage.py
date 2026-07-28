from pathlib import Path

import pytest

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.schemas.attachments import AttachmentPlanRequest
from app.services import attachment_storage


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("drawing.pdf", "drawing.pdf"),
        ("shop drawing.pdf", "shop_drawing.pdf"),
        ("../../secret.env", "secret.env"),
        ("/private/tmp/report.xlsx", "report.xlsx"),
        ("", "attachment.bin"),
    ],
)
def test_sanitize_filename(name, expected):
    assert attachment_storage.sanitize_filename(name) == expected


def test_long_filename_is_truncated_with_extension():
    result = attachment_storage.sanitize_filename("a" * 300 + ".pdf", 80)
    assert len(result) == 80
    assert result.endswith(".pdf")


def test_storage_key_is_deterministic_and_safe():
    first = attachment_storage.build_storage_key(
        7, "../../project", "rfi", "/absolute/item", "../../drawing.pdf"
    )
    second = attachment_storage.build_storage_key(
        7, "../../project", "rfi", "/absolute/item", "../../drawing.pdf"
    )
    assert first == second
    assert first == (
        "connection-7/project-project/rfi-absolute-item/drawing.pdf"
    )
    assert ".." not in Path(first).parts
    assert not Path(first).is_absolute()


def test_plan_hashes_url_without_retaining_it():
    raw_url = "https://example.invalid/signed?secret=must-not-store"
    plan = attachment_storage.plan_attachment_storage(
        AttachmentPlanRequest(
            connection_id=1,
            source_type="rfi",
            procore_project_id="project-test",
            procore_item_id="rfi-test",
            original_filename="drawing.pdf",
            source_url=raw_url,
        )
    )
    assert plan["source_url_present"] is True
    assert len(plan["source_url_hash"]) == 64
    assert raw_url not in str(plan)


def test_fixture_write_overwrite_and_checksum(tmp_path, db_session):
    config = Settings(
        _env_file=None,
        attachment_storage_root=tmp_path,
        attachment_allow_overwrite=False,
    )
    request = AttachmentPlanRequest(
        connection_id=None,
        source_type="rfi",
        procore_project_id="project-test",
        procore_item_id="rfi-test",
        procore_attachment_id="attachment-test",
        original_filename="fixture.pdf",
    )
    attachment = attachment_storage.create_attachment_manifest_record(
        db_session, request, config
    )
    result = attachment_storage.download_attachment_fixture_only(
        db_session, attachment, config
    )
    assert result.download_status == "downloaded"
    assert len(result.checksum_sha256) == 64
    assert (tmp_path / result.storage_key).read_bytes()
    with pytest.raises(attachment_storage.AttachmentStorageError):
        attachment_storage.download_attachment_fixture_only(
            db_session, attachment, config
        )


def test_failed_write_stores_sanitized_failure(
    monkeypatch, tmp_path, db_session
):
    config = Settings(_env_file=None, attachment_storage_root=tmp_path)
    attachment = attachment_storage.create_attachment_manifest_record(
        db_session,
        AttachmentPlanRequest(
            source_type="unknown",
            original_filename="fixture.bin",
        ),
        config,
    )

    def fail(*_args, **_kwargs):
        raise attachment_storage.AttachmentStorageError(
            "private-path secret-value"
        )

    monkeypatch.setattr(
        attachment_storage.LocalAttachmentStorage, "write_bytes", fail
    )
    with pytest.raises(attachment_storage.AttachmentStorageError) as error:
        attachment_storage.download_attachment_fixture_only(
            db_session, attachment, config
        )
    db_session.refresh(attachment)
    assert "secret-value" not in str(error.value)
    assert "secret-value" not in attachment.failure_message
    assert attachment.download_status == "failed"


def test_attachment_model_has_no_source_url_column():
    columns = set(AttachmentObject.__table__.columns.keys())
    assert "source_url" not in columns
    assert "source_url_hash" in columns

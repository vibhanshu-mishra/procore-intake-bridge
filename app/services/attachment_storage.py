import hashlib
import re
from pathlib import Path, PurePath
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.attachment_objects import AttachmentObject
from app.schemas.attachments import (
    AttachmentDownloadResult,
    AttachmentPlanRequest,
    AttachmentPlanResult,
)


class AttachmentStorageError(RuntimeError):
    """Local attachment storage failed without exposing private paths or URLs."""


class AttachmentStorageBackend(Protocol):
    def write_bytes(self, storage_key: str, content: bytes) -> Path:
        """Write bytes beneath the configured storage root."""


class LocalAttachmentStorage:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.root = self.settings.attachment_storage_root.resolve()

    def write_bytes(self, storage_key: str, content: bytes) -> Path:
        relative = Path(storage_key)
        if relative.is_absolute() or ".." in relative.parts:
            raise AttachmentStorageError("Unsafe attachment storage key.")
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            raise AttachmentStorageError("Attachment path escaped the storage root.")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not self.settings.attachment_allow_overwrite:
            raise AttachmentStorageError(
                "Attachment already exists and overwrite is disabled."
            )
        target.write_bytes(content)
        return target


def sanitize_filename(name: str, max_length: int = 160) -> str:
    normalized = str(name or "").replace("\\", "/").split("/")[-1].strip()
    normalized = "".join(
        character for character in normalized if character.isprintable()
    )
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)
    normalized = normalized.strip("._-")
    if not normalized:
        normalized = "attachment.bin"
    suffix = PurePath(normalized).suffix
    if len(normalized) > max_length:
        suffix = suffix[: min(len(suffix), 20)]
        stem_length = max(1, max_length - len(suffix))
        normalized = f"{PurePath(normalized).stem[:stem_length]}{suffix}"
    return normalized[:max_length]


def build_storage_key(
    connection_id: int | None,
    procore_project_id: str | None,
    source_type: str,
    procore_item_id: str | None,
    filename: str,
    *,
    max_filename_length: int = 160,
) -> str:
    safe_filename = sanitize_filename(filename, max_filename_length)
    connection = str(connection_id) if connection_id is not None else "unknown"
    project = _safe_component(procore_project_id)
    source = _safe_component(source_type)
    item = _safe_component(procore_item_id)
    return (
        f"connection-{connection}/project-{project}/"
        f"{source}-{item}/{safe_filename}"
    )


def plan_attachment_storage(
    request: AttachmentPlanRequest, settings: Settings | None = None
) -> dict:
    resolved = settings or get_settings()
    safe_filename = sanitize_filename(
        request.original_filename,
        resolved.attachment_max_filename_length,
    )
    storage_key = build_storage_key(
        request.connection_id,
        request.procore_project_id,
        request.source_type,
        request.procore_item_id,
        safe_filename,
        max_filename_length=resolved.attachment_max_filename_length,
    )
    source_url_present = bool(request.source_url)
    return {
        "safe_filename": safe_filename,
        "storage_backend": "local",
        "storage_key": storage_key,
        "storage_path": storage_key,
        "source_url_present": source_url_present,
        "source_url_hash": (
            hashlib.sha256(request.source_url.encode()).hexdigest()
            if request.source_url
            else None
        ),
        "download_status": "planned",
    }


def create_attachment_manifest_record(
    session: Session,
    request: AttachmentPlanRequest,
    settings: Settings | None = None,
    *,
    commit: bool = True,
) -> AttachmentObject:
    plan = plan_attachment_storage(request, settings)
    existing = _find_existing(session, request)
    attachment = existing or AttachmentObject()
    attachment.intake_record_id = request.intake_record_id
    attachment.sync_run_id = request.sync_run_id
    attachment.connection_id = request.connection_id
    attachment.sync_profile_id = request.sync_profile_id
    attachment.source_type = request.source_type
    attachment.procore_project_id = request.procore_project_id
    attachment.procore_item_id = request.procore_item_id
    attachment.procore_attachment_id = request.procore_attachment_id
    attachment.original_filename = sanitize_filename(
        request.original_filename, 500
    )
    attachment.safe_filename = plan["safe_filename"]
    attachment.content_type = request.content_type
    attachment.size_bytes = request.size_bytes
    attachment.source_url_present = plan["source_url_present"]
    attachment.source_url_hash = plan["source_url_hash"]
    attachment.storage_backend = plan["storage_backend"]
    attachment.storage_key = plan["storage_key"]
    attachment.storage_path = plan["storage_path"]
    if attachment.download_status != "downloaded":
        attachment.download_status = "planned"
        attachment.failure_code = None
        attachment.failure_message = None
    if existing is None:
        session.add(attachment)
    if commit:
        session.commit()
        session.refresh(attachment)
    else:
        session.flush()
    return attachment


def download_attachment_fixture_only(
    session: Session,
    attachment: AttachmentObject,
    settings: Settings | None = None,
    *,
    fixture_label: str = "deterministic-fixture",
) -> AttachmentDownloadResult:
    resolved = settings or get_settings()
    if not resolved.attachment_fixture_downloads_only:
        raise AttachmentStorageError(
            "A5 supports fixture attachment downloads only."
        )
    content = (
        "Procore Intake Bridge fixture attachment\n"
        f"{attachment.storage_key}\n{fixture_label}\n"
    ).encode()
    try:
        path = write_fixture_attachment(
            attachment.storage_key,
            content,
            LocalAttachmentStorage(resolved),
        )
    except AttachmentStorageError:
        attachment.download_status = "failed"
        attachment.failure_code = "FixtureStorageError"
        attachment.failure_message = (
            "Fixture attachment write failed; private path details were omitted."
        )
        session.commit()
        raise AttachmentStorageError(
            "Fixture attachment write failed safely."
        ) from None
    attachment.download_status = "downloaded"
    attachment.size_bytes = len(content)
    attachment.checksum_sha256 = calculate_sha256(path)
    attachment.failure_code = None
    attachment.failure_message = None
    session.commit()
    session.refresh(attachment)
    return AttachmentDownloadResult(
        attachment_id=attachment.id,
        safe_filename=attachment.safe_filename,
        storage_key=attachment.storage_key,
        storage_path=attachment.storage_path,
        download_status=attachment.download_status,
        size_bytes=attachment.size_bytes,
        checksum_sha256=attachment.checksum_sha256,
        message="Deterministic fixture attachment written to local storage.",
    )


def write_fixture_attachment(
    storage_key: str,
    content: bytes,
    backend: AttachmentStorageBackend,
) -> Path:
    return backend.write_bytes(storage_key, content)


def calculate_sha256(value: Path | bytes) -> str:
    content = value.read_bytes() if isinstance(value, Path) else value
    return hashlib.sha256(content).hexdigest()


def attachment_plan_result(
    attachment: AttachmentObject | None,
    request: AttachmentPlanRequest,
    settings: Settings | None = None,
) -> AttachmentPlanResult:
    plan = plan_attachment_storage(request, settings)
    if attachment is not None:
        plan = {
            "safe_filename": attachment.safe_filename,
            "storage_backend": attachment.storage_backend,
            "storage_key": attachment.storage_key,
            "storage_path": attachment.storage_path,
            "source_url_present": attachment.source_url_present,
            "source_url_hash": attachment.source_url_hash,
            "download_status": attachment.download_status,
        }
    return AttachmentPlanResult(
        attachment_id=attachment.id if attachment else None,
        persisted=attachment is not None,
        **plan,
        message=(
            "Attachment manifest record created; no download was attempted."
            if attachment
            else "Attachment storage plan created without persistence."
        ),
    )


def _find_existing(
    session: Session, request: AttachmentPlanRequest
) -> AttachmentObject | None:
    if request.procore_attachment_id is None:
        return None
    return session.scalar(
        select(AttachmentObject).where(
            AttachmentObject.connection_id == request.connection_id,
            AttachmentObject.procore_project_id == request.procore_project_id,
            AttachmentObject.source_type == request.source_type,
            AttachmentObject.procore_item_id == request.procore_item_id,
            AttachmentObject.procore_attachment_id
            == request.procore_attachment_id,
        )
    )


def _safe_component(value: str | None) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "unknown"))
    normalized = normalized.strip("-_")[:100]
    return normalized or "unknown"

import hashlib
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from app.config import Settings


class AttachmentStorageKeyError(ValueError):
    """A storage key is unsafe without echoing the supplied value."""


def normalize_storage_key(key: str) -> str:
    return re.sub(r"/+", "/", str(key).replace("\\", "/").strip())


def is_safe_relative_storage_path(value: str) -> bool:
    normalized = normalize_storage_key(value)
    if not normalized or any(ord(character) < 32 for character in normalized):
        return False
    if normalized.startswith("/") or Path(normalized).is_absolute():
        return False
    if urlsplit(normalized).scheme or "://" in normalized:
        return False
    parts = PurePosixPath(normalized).parts
    return bool(parts) and all(part not in {"", ".", ".."} for part in parts)


def validate_storage_key(key: str, settings: Settings | None = None) -> str:
    normalized = normalize_storage_key(key)
    if not is_safe_relative_storage_path(normalized):
        raise AttachmentStorageKeyError("Attachment storage key is unsafe.")
    if settings and settings.attachment_storage_require_safe_keys:
        if normalized != key.replace("\\", "/").strip():
            raise AttachmentStorageKeyError("Attachment storage key is not normalized.")
    return normalized


def mask_storage_key(key: str) -> str:
    try:
        normalized = validate_storage_key(key)
    except AttachmentStorageKeyError:
        return "[invalid-storage-key]"
    name = PurePosixPath(normalized).name
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:12]
    suffix = PurePosixPath(name).suffix[:12]
    return f"object-{digest}{suffix}"


def build_safe_storage_key(
    connection_id: int | None,
    project_id: str | None,
    source_type: str,
    item_id: str | None,
    filename: str,
    *,
    max_filename_length: int = 160,
) -> str:
    safe_name = _safe_filename(filename, max_filename_length)
    key = (
        f"connection-{_component(connection_id)}/project-{_component(project_id)}/"
        f"{_component(source_type)}-{_component(item_id)}/{safe_name}"
    )
    return validate_storage_key(key)


def summarize_content_type(content_type: str | None) -> str:
    normalized = str(content_type or "").split(";", 1)[0].strip().casefold()
    if not normalized or "/" not in normalized:
        return "unknown"
    return normalized[:200]


def classify_content_type(content_type: str | None, settings: Settings) -> str:
    normalized = summarize_content_type(content_type)
    allowed = {
        item.strip().casefold()
        for item in settings.attachment_storage_allowed_content_types.split(",")
        if item.strip()
    }
    if normalized == "unknown":
        return "quarantined" if settings.attachment_storage_quarantine_unknown_types else "unknown"
    if allowed and normalized not in allowed:
        return "quarantined"
    return "allowed"


def calculate_attachment_integrity_metadata(value: bytes | Path) -> dict[str, int | str]:
    content = value.read_bytes() if isinstance(value, Path) else value
    return {"checksum_sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}


def _component(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value if value is not None else "unknown"))
    return normalized.strip("-_")[:100] or "unknown"


def _safe_filename(value: str, max_length: int) -> str:
    name = normalize_storage_key(value).split("/")[-1]
    name = "".join(character for character in name if character.isprintable())
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-") or "attachment.bin"
    suffix = PurePosixPath(name).suffix[:20]
    if len(name) > max_length:
        name = f"{PurePosixPath(name).stem[: max(1, max_length - len(suffix))]}{suffix}"
    return name[:max_length]

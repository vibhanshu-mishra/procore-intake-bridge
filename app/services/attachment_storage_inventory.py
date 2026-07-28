from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.services.attachment_storage_keys import classify_content_type, mask_storage_key
from app.services.attachment_storage_provider import (
    AttachmentStorageProvider,
    AttachmentStorageProviderError,
)


def collect_attachment_storage_inventory(
    db_session: Session,
    provider: AttachmentStorageProvider,
    limit: int = 1000,
    settings: Settings | None = None,
) -> list[dict]:
    rows = list(
        db_session.scalars(select(AttachmentObject).order_by(AttachmentObject.id).limit(limit))
    )
    items = []
    for row in rows:
        exists: bool | None = None
        if provider.name in {"local", "test"}:
            try:
                exists = provider.exists(row.storage_key)
            except AttachmentStorageProviderError:
                exists = False
        items.append(
            {
                "id": row.id,
                "provider": row.storage_backend,
                "storage_key": mask_storage_key(row.storage_key),
                "download_status": row.download_status,
                "content_type_classification": classify_content_type(
                    row.content_type, settings or provider.settings
                ),
                "object_exists": exists,
            }
        )
    return items


def summarize_attachment_storage_inventory(items: list[dict]) -> dict:
    return {
        "total": len(items),
        "by_download_status": dict(Counter(item["download_status"] for item in items)),
        "by_provider": dict(Counter(item["provider"] for item in items)),
        "by_content_type_classification": dict(
            Counter(item["content_type_classification"] for item in items)
        ),
        "missing_objects": sum(
            item["object_exists"] is False and item["download_status"] == "downloaded"
            for item in items
        ),
        "contents_inspected": False,
        "paths_exposed": False,
    }


def check_manifest_storage_consistency(
    db_session: Session,
    provider: AttachmentStorageProvider,
    limit: int = 1000,
    settings: Settings | None = None,
) -> dict:
    items = collect_attachment_storage_inventory(db_session, provider, limit, settings)
    summary = summarize_attachment_storage_inventory(items)
    return {
        "consistent": summary["missing_objects"] == 0,
        "summary": summary,
        "findings": [
            {
                "attachment_id": item["id"],
                "finding": "downloaded_object_missing",
                "storage_key": item["storage_key"],
            }
            for item in items
            if item["object_exists"] is False and item["download_status"] == "downloaded"
        ],
    }

from app.schemas.sync import AttachmentManifestEntry


def build_attachment_manifest(source_type: str, item: dict) -> list[AttachmentManifestEntry]:
    return [
        AttachmentManifestEntry(
            source_type=source_type,
            procore_project_id=str(item["project_id"]),
            procore_item_id=str(item["id"]),
            procore_attachment_id=str(attachment["id"]),
            filename=attachment["filename"],
            content_type=attachment.get("content_type"),
        )
        for attachment in item.get("attachments", [])
    ]

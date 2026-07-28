from sqlalchemy import select

from app.database import SessionLocal, create_db_and_tables
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeAttachment
from app.schemas.attachments import AttachmentPlanRequest
from app.services.attachment_storage import create_attachment_manifest_record


def main() -> None:
    create_db_and_tables()
    created = 0
    with SessionLocal() as session:
        intake_attachments = list(session.scalars(select(IntakeAttachment)))
        for metadata in intake_attachments:
            record = metadata.record
            connection_id = record.sync_run.connection_id
            existing = session.scalar(
                select(AttachmentObject).where(
                    AttachmentObject.connection_id == connection_id,
                    AttachmentObject.procore_project_id
                    == record.procore_project_id,
                    AttachmentObject.source_type == record.source_type,
                    AttachmentObject.procore_item_id == record.procore_item_id,
                    AttachmentObject.procore_attachment_id
                    == metadata.procore_attachment_id,
                )
            )
            if existing:
                continue
            create_attachment_manifest_record(
                session,
                AttachmentPlanRequest(
                    intake_record_id=record.id,
                    sync_run_id=record.sync_run_id,
                    connection_id=connection_id,
                    source_type=record.source_type,
                    procore_project_id=record.procore_project_id,
                    procore_item_id=record.procore_item_id,
                    procore_attachment_id=metadata.procore_attachment_id,
                    original_filename=metadata.filename,
                    content_type=metadata.content_type,
                ),
                commit=False,
            )
            created += 1
        session.commit()
        total = len(list(session.scalars(select(AttachmentObject))))
    print(f"Attachment manifests: total={total}, created={created}, downloads=0")


if __name__ == "__main__":
    main()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.schemas.attachments import (
    AttachmentDownloadRequest,
    AttachmentDownloadResult,
    AttachmentObjectRead,
    AttachmentPlanRequest,
    AttachmentPlanResult,
)
from app.services.attachment_storage import (
    AttachmentStorageError,
    attachment_plan_result,
    create_attachment_manifest_record,
    download_attachment_fixture_only,
)

router = APIRouter(tags=["attachments"])


@router.get("/attachments", response_model=list[AttachmentObjectRead])
def list_attachments(
    download_status: str | None = None,
    session: Session = Depends(get_session),
):
    statement = select(AttachmentObject)
    if download_status:
        statement = statement.where(
            AttachmentObject.download_status == download_status
        )
    return list(session.scalars(statement.order_by(AttachmentObject.id)))


@router.get("/attachments/{attachment_id}", response_model=AttachmentObjectRead)
def get_attachment(
    attachment_id: int, session: Session = Depends(get_session)
):
    return _attachment_or_404(session, attachment_id)


@router.post("/attachments/plan", response_model=AttachmentPlanResult)
def plan_attachment(
    payload: AttachmentPlanRequest, session: Session = Depends(get_session)
) -> AttachmentPlanResult:
    if payload.intake_record_id is not None and session.get(
        IntakeRecord, payload.intake_record_id
    ) is None:
        raise HTTPException(status_code=404, detail="Intake record not found")
    attachment = create_attachment_manifest_record(session, payload)
    return attachment_plan_result(attachment, payload)


@router.post(
    "/attachments/{attachment_id}/fixture-download",
    response_model=AttachmentDownloadResult,
)
def fixture_download(
    attachment_id: int,
    payload: AttachmentDownloadRequest | None = None,
    session: Session = Depends(get_session),
) -> AttachmentDownloadResult:
    attachment = _attachment_or_404(session, attachment_id)
    try:
        return download_attachment_fixture_only(
            session,
            attachment,
            fixture_label=(
                payload.fixture_label if payload else "deterministic-fixture"
            ),
        )
    except AttachmentStorageError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/intake-records/{intake_record_id}/attachments",
    response_model=list[AttachmentObjectRead],
)
def intake_record_attachments(
    intake_record_id: int, session: Session = Depends(get_session)
):
    if session.get(IntakeRecord, intake_record_id) is None:
        raise HTTPException(status_code=404, detail="Intake record not found")
    return list(
        session.scalars(
            select(AttachmentObject)
            .where(AttachmentObject.intake_record_id == intake_record_id)
            .order_by(AttachmentObject.id)
        )
    )


def _attachment_or_404(
    session: Session, attachment_id: int
) -> AttachmentObject:
    attachment = session.get(AttachmentObject, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment

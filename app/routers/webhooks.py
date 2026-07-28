import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.schemas.webhooks import (
    WebhookEventListItem,
    WebhookEventRead,
    WebhookReceiveResult,
)
from app.security.secret_provider_factory import build_secret_provider
from app.security.webhook_signature import (
    WebhookSignatureError,
    verify_webhook_signature,
)
from app.services.event_queue import (
    enqueue_webhook_event,
    get_webhook_event,
    list_webhook_events,
    replay_webhook_event,
)

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/procore", response_model=WebhookReceiveResult)
async def receive_procore_webhook(
    request: Request, session: Session = Depends(get_session)
) -> WebhookReceiveResult:
    return await _receive(request, session, persist=True)


@router.post("/webhooks/procore/dry-run", response_model=WebhookReceiveResult)
async def dry_run_procore_webhook(
    request: Request, session: Session = Depends(get_session)
) -> WebhookReceiveResult:
    return await _receive(request, session, persist=False)


@router.get("/webhook-events", response_model=list[WebhookEventListItem])
def webhook_events(
    processing_status: Literal[
        "queued", "processing", "processed", "skipped", "failed"
    ]
    | None = Query(default=None),
    resource_type: Literal["rfi", "submittal", "unknown"] | None = Query(
        default=None
    ),
    session: Session = Depends(get_session),
):
    return list_webhook_events(
        session,
        processing_status=processing_status,
        resource_type=resource_type,
    )


@router.get("/webhook-events/{webhook_event_id}", response_model=WebhookEventRead)
def webhook_event(
    webhook_event_id: int, session: Session = Depends(get_session)
):
    event = get_webhook_event(session, webhook_event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    return event


@router.post(
    "/webhook-events/{webhook_event_id}/replay",
    response_model=WebhookEventRead,
)
def replay_event(
    webhook_event_id: int, session: Session = Depends(get_session)
):
    event = get_webhook_event(session, webhook_event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    return replay_webhook_event(session, event)


async def _receive(
    request: Request, session: Session, *, persist: bool
) -> WebhookReceiveResult:
    settings = get_settings()
    if not settings.webhooks_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook receiving is disabled.",
        )
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Webhook body must be a JSON object.")

    try:
        signature_result = verify_webhook_signature(
            raw_body,
            request.headers,
            build_secret_provider(settings),
            settings,
        )
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    safe_headers = {}
    event_header = request.headers.get(settings.webhook_event_id_header)
    if event_header:
        safe_headers[settings.webhook_event_id_header] = event_header
    event, duplicate = enqueue_webhook_event(
        session,
        payload,
        safe_headers,
        signature_result,
        persist=persist,
    )
    return WebhookReceiveResult(
        accepted=True,
        persisted=persist and not duplicate,
        duplicate=duplicate,
        webhook_event_id=event.id if persist else None,
        event_id=event.event_id,
        resource_type=event.resource_type,
        action=event.action,
        signature_status=event.signature_status,
        processing_status=event.processing_status,
        message=(
            "Duplicate event already exists."
            if duplicate
            else (
                "Webhook dry run completed without persistence."
                if not persist
                else "Webhook event stored for later processing."
            )
        ),
    )

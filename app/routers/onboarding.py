from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.connections import DMSAConnection
from app.models.onboarding_packets import OnboardingPacket
from app.models.sync_profiles import SyncProfile
from app.schemas.onboarding import (
    OnboardingPacketExportResponse,
    OnboardingPacketGenerateRequest,
    OnboardingPacketGenerateResponse,
    OnboardingPacketPreviewRequest,
    OnboardingPacketPreviewResponse,
    OnboardingPacketRead,
    PermissionChecklistItem,
)
from app.services.onboarding_packet import (
    build_permission_checklist,
    export_onboarding_packet_local,
    generate_onboarding_packet,
    preview_onboarding_packet,
)

router = APIRouter(tags=["onboarding"])


@router.get(
    "/onboarding/default-permissions",
    response_model=list[PermissionChecklistItem],
)
def default_permissions():
    return build_permission_checklist()


@router.post(
    "/onboarding/preview", response_model=OnboardingPacketPreviewResponse
)
def preview_packet(payload: OnboardingPacketPreviewRequest):
    return preview_onboarding_packet(payload)


@router.post(
    "/onboarding/generate", response_model=OnboardingPacketGenerateResponse
)
def generate_packet(
    payload: OnboardingPacketGenerateRequest,
    session: Session = Depends(get_session),
):
    enriched = _enrich_from_connection(session, payload)
    packet, preview = generate_onboarding_packet(session, enriched)
    return OnboardingPacketGenerateResponse(
        packet_id=packet.id,
        **preview.model_dump(exclude={"persisted"}),
        persisted=True,
    )


@router.get("/onboarding-packets", response_model=list[OnboardingPacketRead])
def list_packets(session: Session = Depends(get_session)):
    return list(
        session.scalars(
            select(OnboardingPacket).order_by(OnboardingPacket.id.desc())
        )
    )


@router.get(
    "/onboarding-packets/{packet_id}", response_model=OnboardingPacketRead
)
def get_packet(packet_id: int, session: Session = Depends(get_session)):
    return _packet_or_404(session, packet_id)


@router.post(
    "/connections/{connection_id}/onboarding-packet",
    response_model=OnboardingPacketGenerateResponse,
)
def generate_connection_packet(
    connection_id: int,
    payload: OnboardingPacketGenerateRequest | None = None,
    session: Session = Depends(get_session),
):
    if payload is None:
        payload = OnboardingPacketGenerateRequest(
            recipient_company_name="GC_OWNER_COMPANY_PLACEHOLDER",
            connection_id=connection_id,
        )
    else:
        payload = payload.model_copy(update={"connection_id": connection_id})
    enriched = _enrich_from_connection(session, payload)
    packet, preview = generate_onboarding_packet(session, enriched)
    return OnboardingPacketGenerateResponse(
        packet_id=packet.id,
        **preview.model_dump(exclude={"persisted"}),
        persisted=True,
    )


@router.post(
    "/onboarding-packets/{packet_id}/export-local",
    response_model=OnboardingPacketExportResponse,
)
def export_packet_local(
    packet_id: int, session: Session = Depends(get_session)
):
    return export_onboarding_packet_local(_packet_or_404(session, packet_id))


def _enrich_from_connection(
    session: Session, payload: OnboardingPacketGenerateRequest
) -> OnboardingPacketGenerateRequest:
    if payload.connection_id is None:
        return payload
    connection = session.get(DMSAConnection, payload.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    profiles = list(
        session.scalars(
            select(SyncProfile).where(
                SyncProfile.connection_id == connection.id
            )
        )
    )
    project_ids = list(
        dict.fromkeys(
            [
                *payload.requested_project_ids,
                *connection.permitted_project_ids,
                *(profile.procore_project_id for profile in profiles),
            ]
        )
    )
    tools = list(payload.requested_tools)
    if any(profile.sync_rfis for profile in profiles) and "rfis" not in tools:
        tools.append("rfis")
    if (
        any(profile.sync_submittals for profile in profiles)
        and "submittals" not in tools
    ):
        tools.append("submittals")
    return payload.model_copy(
        update={
            "requested_project_ids": project_ids,
            "requested_tools": tools,
        }
    )


def _packet_or_404(session: Session, packet_id: int) -> OnboardingPacket:
    packet = session.get(OnboardingPacket, packet_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Onboarding packet not found")
    return packet

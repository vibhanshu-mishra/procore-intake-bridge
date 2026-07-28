from datetime import UTC, datetime

from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.models.onboarding_packets import OnboardingPacket
from app.models.sync_runs import SyncRun
from app.models.webhook_events import WebhookEvent
from app.services.admin_dashboard import build_admin_overview


def test_populated_overview_counts_and_sanitizes_every_resource(
    db_session, connection, sync_profile
):
    run = SyncRun(
        connection_id=connection.id,
        status="completed",
        record_count=1,
        attachment_count=1,
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    record = IntakeRecord(
        source_type="rfi",
        procore_project_id="project-private-1001",
        procore_item_id="item-private-2002",
        number="RFI-PRIVATE-3",
        title="Customer confidential title",
        status="open",
        due_date=None,
        received_at=None,
        source_updated_at=None,
        raw_payload_json={"token": "payload-secret"},
        attachment_count=1,
        sync_run_id=run.id,
    )
    db_session.add(record)
    db_session.flush()
    db_session.add_all(
        [
            AttachmentObject(
                intake_record_id=record.id,
                sync_run_id=run.id,
                connection_id=connection.id,
                sync_profile_id=sync_profile.id,
                source_type="rfi",
                procore_project_id="project-private-1001",
                procore_item_id="item-private-2002",
                procore_attachment_id="attachment-private-4",
                original_filename="customer-confidential.pdf",
                safe_filename="customer-confidential.pdf",
                content_type="application/pdf",
                size_bytes=42,
                source_url_present=True,
                source_url_hash="url-hash-secret",
                storage_backend="local",
                storage_key="private/key/customer-confidential.pdf",
                storage_path="/private/customer/customer-confidential.pdf",
                download_status="planned",
            ),
            WebhookEvent(
                connection_id=connection.id,
                sync_profile_id=sync_profile.id,
                event_id="event-private-5005",
                event_type="rfi.updated",
                resource_type="rfi",
                action="updated",
                payload_json={"authorization": "payload-secret"},
                normalized_json={"url": "https://example.invalid/signed"},
                signature_status="valid",
            ),
            OnboardingPacket(
                connection_id=connection.id,
                sync_profile_id=sync_profile.id,
                packet_name="Private packet name",
                recipient_company_name="Private recipient",
                requester_company_name="Private requester",
                app_name="Private app",
                app_version_key_ref="secret/app-key",
                requested_project_ids_json=["project-private-1001"],
                requested_tools_json=["rfis"],
                requested_permissions_json=[],
                safety_summary_json=[],
                generated_markdown="generated private content",
                generated_json={"token": "generated-secret"},
            ),
        ]
    )
    db_session.commit()

    overview = build_admin_overview(db_session)
    assert {card.label: card.count for card in overview.count_cards} == {
        "Connections": 1,
        "Sync profiles": 1,
        "Sync runs": 1,
        "Intake records": 1,
        "Attachments": 1,
        "Webhook events": 1,
        "Onboarding packets": 1,
    }
    serialized = str(overview.model_dump(mode="json"))
    for forbidden in (
        "secret/test-placeholder",
        "payload-secret",
        "generated-secret",
        "generated private content",
        "Private recipient",
        "customer-confidential",
        "url-hash-secret",
        "https://example.invalid",
        "/private/customer",
        "project-private-1001",
        "item-private-2002",
    ):
        assert forbidden not in serialized
    assert overview.recent_attachments[0].filename_display.endswith(".pdf")
    assert overview.recent_webhook_events[0].event_id_masked == "eve***005"

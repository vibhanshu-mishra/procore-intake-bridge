"""Deterministic initial schema for the current SQLAlchemy models.

Revision ID: 0001_initial_schema
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dmsa_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("procore_company_id", sa.String(length=100), nullable=False),
        sa.Column(
            "environment",
            sa.Enum("SANDBOX", "PRODUCTION", name="procoreenvironment"),
            nullable=False,
        ),
        sa.Column("auth_mode", sa.Enum("DMSA_CLIENT_CREDENTIALS", name="authmode"), nullable=False),
        sa.Column("permitted_project_ids", sa.JSON(), nullable=False),
        sa.Column("enabled_tools", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "ACTIVE", "DEGRADED", "REVOKED", name="connectionstatus"),
            nullable=False,
        ),
        sa.Column("client_id_ref", sa.String(length=255), nullable=True),
        sa.Column("secret_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_dmsa_connections_procore_company_id"),
        "dmsa_connections",
        ["procore_company_id"],
        unique=False,
    )
    op.create_table(
        "sync_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("procore_project_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("sync_rfis", sa.Boolean(), nullable=False),
        sa.Column("sync_submittals", sa.Boolean(), nullable=False),
        sa.Column("polling_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_watermark_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_owner", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["dmsa_connections.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id", "procore_project_id", name="uq_sync_profile_connection_project"
        ),
    )
    op.create_index(
        op.f("ix_sync_profiles_connection_id"), "sync_profiles", ["connection_id"], unique=False
    )
    op.create_index(
        op.f("ix_sync_profiles_procore_project_id"),
        "sync_profiles",
        ["procore_project_id"],
        unique=False,
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("attachment_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["dmsa_connections.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sync_runs_connection_id"), "sync_runs", ["connection_id"], unique=False
    )
    op.create_table(
        "intake_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("procore_project_id", sa.String(length=100), nullable=False),
        sa.Column("procore_item_id", sa.String(length=100), nullable=False),
        sa.Column("number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("attachment_count", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sync_run_id"],
            ["sync_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "procore_project_id", "procore_item_id", name="uq_source_item"
        ),
    )
    op.create_index(
        op.f("ix_intake_records_procore_project_id"),
        "intake_records",
        ["procore_project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intake_records_source_type"), "intake_records", ["source_type"], unique=False
    )
    op.create_index(
        op.f("ix_intake_records_sync_run_id"), "intake_records", ["sync_run_id"], unique=False
    )
    op.create_table(
        "onboarding_packets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("sync_profile_id", sa.Integer(), nullable=True),
        sa.Column("packet_name", sa.String(length=200), nullable=False),
        sa.Column("packet_type", sa.String(length=100), nullable=False),
        sa.Column("recipient_company_name", sa.String(length=200), nullable=False),
        sa.Column("recipient_contact_name", sa.String(length=200), nullable=True),
        sa.Column("requester_company_name", sa.String(length=200), nullable=False),
        sa.Column("requester_contact_name", sa.String(length=200), nullable=True),
        sa.Column("app_name", sa.String(length=200), nullable=False),
        sa.Column("app_version_key_ref", sa.String(length=255), nullable=True),
        sa.Column("requested_project_ids_json", sa.JSON(), nullable=False),
        sa.Column("requested_tools_json", sa.JSON(), nullable=False),
        sa.Column("requested_permissions_json", sa.JSON(), nullable=False),
        sa.Column("safety_summary_json", sa.JSON(), nullable=False),
        sa.Column("generated_markdown", sa.Text(), nullable=False),
        sa.Column("generated_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["dmsa_connections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sync_profile_id"],
            ["sync_profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_onboarding_packets_connection_id"),
        "onboarding_packets",
        ["connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_packets_sync_profile_id"),
        "onboarding_packets",
        ["sync_profile_id"],
        unique=False,
    )
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("sync_profile_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("procore_company_id", sa.String(length=100), nullable=True),
        sa.Column("procore_project_id", sa.String(length=100), nullable=True),
        sa.Column("procore_item_id", sa.String(length=100), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("normalized_json", sa.JSON(), nullable=False),
        sa.Column("signature_status", sa.String(length=30), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_owner", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["dmsa_connections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sync_profile_id"],
            ["sync_profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_webhook_event_id"),
    )
    op.create_index(
        op.f("ix_webhook_events_available_at"), "webhook_events", ["available_at"], unique=False
    )
    op.create_index(
        op.f("ix_webhook_events_connection_id"), "webhook_events", ["connection_id"], unique=False
    )
    op.create_index(
        op.f("ix_webhook_events_event_id"), "webhook_events", ["event_id"], unique=False
    )
    op.create_index(
        op.f("ix_webhook_events_procore_company_id"),
        "webhook_events",
        ["procore_company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_events_procore_project_id"),
        "webhook_events",
        ["procore_project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_events_sync_profile_id"),
        "webhook_events",
        ["sync_profile_id"],
        unique=False,
    )
    op.create_table(
        "attachment_objects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intake_record_id", sa.Integer(), nullable=True),
        sa.Column("sync_run_id", sa.Integer(), nullable=True),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("sync_profile_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("procore_project_id", sa.String(length=100), nullable=True),
        sa.Column("procore_item_id", sa.String(length=100), nullable=True),
        sa.Column("procore_attachment_id", sa.String(length=100), nullable=True),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("safe_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("source_url_present", sa.Boolean(), nullable=False),
        sa.Column("source_url_hash", sa.String(length=64), nullable=True),
        sa.Column("storage_backend", sa.String(length=30), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("download_status", sa.String(length=30), nullable=False),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["dmsa_connections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["intake_record_id"],
            ["intake_records.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sync_profile_id"],
            ["sync_profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sync_run_id"],
            ["sync_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id",
            "procore_project_id",
            "source_type",
            "procore_item_id",
            "procore_attachment_id",
            name="uq_attachment_source_identity",
        ),
    )
    op.create_index(
        op.f("ix_attachment_objects_connection_id"),
        "attachment_objects",
        ["connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attachment_objects_intake_record_id"),
        "attachment_objects",
        ["intake_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attachment_objects_procore_project_id"),
        "attachment_objects",
        ["procore_project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attachment_objects_sync_profile_id"),
        "attachment_objects",
        ["sync_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attachment_objects_sync_run_id"),
        "attachment_objects",
        ["sync_run_id"],
        unique=False,
    )
    op.create_table(
        "intake_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intake_record_id", sa.Integer(), nullable=False),
        sa.Column("procore_attachment_id", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=True),
        sa.Column("source_url_redacted", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["intake_record_id"],
            ["intake_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_intake_attachments_intake_record_id"),
        "intake_attachments",
        ["intake_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_intake_attachments_intake_record_id"), table_name="intake_attachments")
    op.drop_table("intake_attachments")
    op.drop_index(op.f("ix_attachment_objects_sync_run_id"), table_name="attachment_objects")
    op.drop_index(op.f("ix_attachment_objects_sync_profile_id"), table_name="attachment_objects")
    op.drop_index(op.f("ix_attachment_objects_procore_project_id"), table_name="attachment_objects")
    op.drop_index(op.f("ix_attachment_objects_intake_record_id"), table_name="attachment_objects")
    op.drop_index(op.f("ix_attachment_objects_connection_id"), table_name="attachment_objects")
    op.drop_table("attachment_objects")
    op.drop_index(op.f("ix_webhook_events_sync_profile_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_procore_project_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_procore_company_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_event_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_connection_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_available_at"), table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_index(op.f("ix_onboarding_packets_sync_profile_id"), table_name="onboarding_packets")
    op.drop_index(op.f("ix_onboarding_packets_connection_id"), table_name="onboarding_packets")
    op.drop_table("onboarding_packets")
    op.drop_index(op.f("ix_intake_records_sync_run_id"), table_name="intake_records")
    op.drop_index(op.f("ix_intake_records_source_type"), table_name="intake_records")
    op.drop_index(op.f("ix_intake_records_procore_project_id"), table_name="intake_records")
    op.drop_table("intake_records")
    op.drop_index(op.f("ix_sync_runs_connection_id"), table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index(op.f("ix_sync_profiles_procore_project_id"), table_name="sync_profiles")
    op.drop_index(op.f("ix_sync_profiles_connection_id"), table_name="sync_profiles")
    op.drop_table("sync_profiles")
    op.drop_index(op.f("ix_dmsa_connections_procore_company_id"), table_name="dmsa_connections")
    op.drop_table("dmsa_connections")

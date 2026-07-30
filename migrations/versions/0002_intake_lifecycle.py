"""Add local intake lifecycle state and event history.

Revision ID: 0002_intake_lifecycle
Revises: 0001_initial_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_intake_lifecycle"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intake_review_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intake_record_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_reason_code", sa.String(length=60), nullable=True),
        sa.Column("current_reason_summary_sanitized", sa.String(length=500), nullable=True),
        sa.Column("actor_hash", sa.String(length=64), nullable=True),
        sa.Column("actor_label_masked", sa.String(length=140), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["intake_record_id"], ["intake_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "intake_record_id", name="uq_intake_review_state_record"
        ),
    )
    op.create_index(
        op.f("ix_intake_review_states_intake_record_id"),
        "intake_review_states",
        ["intake_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intake_review_states_status"),
        "intake_review_states",
        ["status"],
        unique=False,
    )
    op.create_table(
        "intake_review_lifecycle_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intake_record_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=False),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("reason_code", sa.String(length=60), nullable=False),
        sa.Column("reason_summary_sanitized", sa.String(length=500), nullable=False),
        sa.Column("actor_hash", sa.String(length=64), nullable=True),
        sa.Column("actor_label_masked", sa.String(length=140), nullable=True),
        sa.Column("request_id_hash", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["intake_record_id"], ["intake_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_intake_review_lifecycle_events_intake_record_id"),
        "intake_review_lifecycle_events",
        ["intake_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intake_review_lifecycle_events_to_status"),
        "intake_review_lifecycle_events",
        ["to_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intake_review_lifecycle_events_created_at"),
        "intake_review_lifecycle_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_intake_review_lifecycle_events_created_at"),
        table_name="intake_review_lifecycle_events",
    )
    op.drop_index(
        op.f("ix_intake_review_lifecycle_events_to_status"),
        table_name="intake_review_lifecycle_events",
    )
    op.drop_index(
        op.f("ix_intake_review_lifecycle_events_intake_record_id"),
        table_name="intake_review_lifecycle_events",
    )
    op.drop_table("intake_review_lifecycle_events")
    op.drop_index(
        op.f("ix_intake_review_states_status"), table_name="intake_review_states"
    )
    op.drop_index(
        op.f("ix_intake_review_states_intake_record_id"),
        table_name="intake_review_states",
    )
    op.drop_table("intake_review_states")

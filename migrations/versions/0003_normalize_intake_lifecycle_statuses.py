"""Normalize legacy Demo lifecycle labels to the H4 vocabulary.

Revision ID: 0003_normalize_intake_lifecycle_statuses
Revises: 0002_intake_lifecycle

The first Demo seed used ``blocked``/``completed`` lifecycle labels and a
``J2_DEMO_FIXTURE`` reason code before the H4 enum became canonical.  This
allow-listed data migration repairs those rows without adding legacy values to
the current enum.  Unknown values are left in place for the service's
sanitized needs-review read path.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_normalize_intake_lifecycle_statuses"
down_revision: str | Sequence[str] | None = "0002_intake_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE intake_review_states "
        "SET status = 'needs_follow_up' WHERE status = 'blocked'"
    )
    op.execute(
        "UPDATE intake_review_states "
        "SET status = 'reviewed' WHERE status = 'completed'"
    )
    op.execute(
        "UPDATE intake_review_lifecycle_events "
        "SET from_status = 'needs_follow_up' WHERE from_status = 'blocked'"
    )
    op.execute(
        "UPDATE intake_review_lifecycle_events "
        "SET from_status = 'reviewed' WHERE from_status = 'completed'"
    )
    op.execute(
        "UPDATE intake_review_lifecycle_events "
        "SET to_status = 'needs_follow_up' WHERE to_status = 'blocked'"
    )
    op.execute(
        "UPDATE intake_review_lifecycle_events "
        "SET to_status = 'reviewed' WHERE to_status = 'completed'"
    )
    op.execute(
        "UPDATE intake_review_states "
        "SET current_reason_code = 'demo_placeholder_reason' "
        "WHERE current_reason_code = 'J2_DEMO_FIXTURE'"
    )
    op.execute(
        "UPDATE intake_review_lifecycle_events "
        "SET reason_code = 'demo_placeholder_reason' "
        "WHERE reason_code = 'J2_DEMO_FIXTURE'"
    )


def downgrade() -> None:
    # Canonicalization is intentionally not reversed: restoring invalid enum
    # values would recreate the dashboard failure this migration prevents.
    pass

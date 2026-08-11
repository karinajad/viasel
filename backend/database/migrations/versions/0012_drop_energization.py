"""drop project/location target_energization — the schedule owns that date, not us

Added in 0010 and removed on reflection the same day. An energization date is a P6 output,
derived and subject to change; storing it here would make Viasel a second, stale record of
a date it doesn't own, and the architecture is explicit that schedulers are inputs and
consumers rather than the system of record.

What survives is `demand_line.required_by_date` (0009): the need-by for a specific unit,
which is the clock's input to the record rather than a copy of the clock. If prepurchase
ever needs a target date to lock against, it belongs on the LLE tranche, not the project.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("project", "target_energization", schema="viasel")
    op.drop_column("project_location", "target_energization", schema="viasel")


def downgrade() -> None:
    op.add_column("project", sa.Column("target_energization", sa.Date(), nullable=True), schema="viasel")
    op.add_column("project_location", sa.Column("target_energization", sa.Date(), nullable=True), schema="viasel")

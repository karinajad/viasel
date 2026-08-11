"""demand_line.lead_time_weeks replaces is_lle — all of this equipment is long-lead

A boolean "is this long lead" is a question with one answer in OFCI: yes. What the record
needs is the number of weeks, because that is what converts a required-by date into the date
you must be in contract by. The vendor's own lead time already lives on their bid, so the
two can be compared rather than conflated.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "demand_line", sa.Column("lead_time_weeks", sa.Integer(), nullable=True), schema="viasel"
    )
    op.drop_column("demand_line", "is_lle", schema="viasel")


def downgrade() -> None:
    op.add_column(
        "demand_line",
        sa.Column("is_lle", sa.Boolean(), server_default="false", nullable=False),
        schema="viasel",
    )
    op.drop_column("demand_line", "lead_time_weeks", schema="viasel")

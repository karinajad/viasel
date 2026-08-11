"""demand_line.is_lle — long-lead equipment flag on the design register

The register is the input to a prepurchase decision: you cannot choose between locking
216MW and 1GW of long-lead equipment without knowing the quantities and the need-by
dates. `required_by_date` already existed and nothing populated it; the Design register
is where both belong.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "demand_line",
        sa.Column("is_lle", sa.Boolean(), server_default="false", nullable=False),
        schema="viasel",
    )


def downgrade() -> None:
    op.drop_column("demand_line", "is_lle", schema="viasel")

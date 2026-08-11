"""quote cost layers (services/freight/discount/one-time) + disposition reason

A bid's all-in unit price is not its equipment price, and one-time costs (factory
witness test, owner's training) are per ORDER — so they amortize over the lot and
an all-in unit price depends on the quantity. Extending linearly was wrong.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

COLUMNS = ("services_unit", "freight_unit", "discount_unit", "one_time_cost")


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column("quote", sa.Column(name, sa.Numeric(), nullable=True), schema="viasel")
    op.add_column(
        "quote", sa.Column("disposition_reason", sa.String(), nullable=True), schema="viasel"
    )


def downgrade() -> None:
    op.drop_column("quote", "disposition_reason", schema="viasel")
    for name in COLUMNS:
        op.drop_column("quote", name, schema="viasel")

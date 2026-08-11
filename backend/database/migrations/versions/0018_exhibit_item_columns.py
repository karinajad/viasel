"""exhibit_item columns to match the actual exhibit tabs

Read the five tabs properly this time. Their columns are specific and the differences carry
meaning: the delivery schedule holds a Vendor Delivery Date beside a ROJ Date and a
Designation; a bill of materials asks Included?; spares carry their own LLE lead time in
weeks; Schedule D asks Required? and a Need-By Date against one of nine named triggers.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

COLS = [
    ("vendor_delivery_date", sa.Date()),
    ("designation", sa.String()),
    ("is_included", sa.Boolean()),
    ("is_required", sa.Boolean()),
    ("lead_time_weeks", sa.Integer()),
]


def upgrade() -> None:
    for name, kind in COLS:
        op.add_column("exhibit_item", sa.Column(name, kind, nullable=True), schema="viasel")


def downgrade() -> None:
    for name, _ in COLS:
        op.drop_column("exhibit_item", name, schema="viasel")

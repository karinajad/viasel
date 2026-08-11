"""exhibit_item — the exhibit content the record can't derive, entered per agreement

Cover sheet, equipment list and legend are views of the record. The other six tabs of the
exhibit workbook are contract-time content: bill of materials, spare parts, delivery
schedule, shipping capacity, required documents. Those are entered, per vendor, and each row
can point at the scope line it covers — which is what ties an exhibit back to the demand
that was assigned at sourcing rather than floating free of it.

Revision ID: 0015
Revises: 0014
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # creates exhibit_item


def downgrade() -> None:
    op.drop_table("exhibit_item", schema="viasel")

"""vendor + vendor_contact — vendors as records, and quote.vendor_id pointing at them

Free-typed vendor names are why spec §11 vendor reliability can't accumulate: "Eaton" and
"Eaton Corp" are two vendors, so quoted-vs-actual never lines up. `quote.vendor` stays as
the text that was typed (existing rows keep their meaning) and `vendor_id` is added
alongside it, so the link can be adopted without a backfill guess.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # vendor + vendor_contact

    op.add_column("quote", sa.Column("vendor_id", sa.Uuid(), nullable=True), schema="viasel")
    op.create_foreign_key(
        "quote_vendor_id_fkey", "quote", "vendor", ["vendor_id"], ["id"],
        source_schema="viasel", referent_schema="viasel",
    )


def downgrade() -> None:
    op.drop_constraint("quote_vendor_id_fkey", "quote", type_="foreignkey", schema="viasel")
    op.drop_column("quote", "vendor_id", schema="viasel")
    op.drop_table("vendor_contact", schema="viasel")
    op.drop_table("vendor", schema="viasel")

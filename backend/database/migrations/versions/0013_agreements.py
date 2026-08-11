"""agreement + scope_line.agreement_id — award stops dead-ending

Award wrote scope lines and nothing consumed them. An agreement is what commits them, and
per spec §12 its contract value is derived from those lines rather than stored, so the
document and the record cannot hold two different totals. Exhibits are views of this
(§16), which is why there is nowhere here to attach one.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # creates agreement

    op.add_column("scope_line", sa.Column("agreement_id", sa.Uuid(), nullable=True), schema="viasel")
    op.create_foreign_key(
        "scope_line_agreement_id_fkey", "scope_line", "agreement",
        ["agreement_id"], ["id"], source_schema="viasel", referent_schema="viasel",
    )


def downgrade() -> None:
    op.drop_constraint("scope_line_agreement_id_fkey", "scope_line", type_="foreignkey", schema="viasel")
    op.drop_column("scope_line", "agreement_id", schema="viasel")
    op.drop_table("agreement", schema="viasel")

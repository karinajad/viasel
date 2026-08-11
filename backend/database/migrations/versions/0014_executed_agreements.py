"""executed_agreement + field_divergence — Viasel holds the signed version, doesn't own it

0013 gave the agreement `issue` and `execute` states, which modelled Viasel as the system
that owns the instrument lifecycle. It isn't: the client executes agreements wherever they
already do, and per spec §16 Viasel's job is to author the exhibit data, then take the
executed version back and reconcile it field by field.

So the agreement's own state covers our side only — drafted | released | withdrawn — and
execution becomes a fact recorded on the document we received, alongside where that document
actually lives (source system + external ref).

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("agreement", "issued_date", new_column_name="released_date", schema="viasel")
    op.drop_column("agreement", "execution_date", schema="viasel")
    op.execute("update viasel.agreement set state = 'drafted' where state = 'draft'")
    op.execute("update viasel.agreement set state = 'released' where state in ('issued', 'executed')")

    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # executed_agreement + field_divergence


def downgrade() -> None:
    op.drop_table("field_divergence", schema="viasel")
    op.drop_table("executed_agreement", schema="viasel")
    op.add_column("agreement", sa.Column("execution_date", sa.Date(), nullable=True), schema="viasel")
    op.alter_column("agreement", "released_date", new_column_name="issued_date", schema="viasel")

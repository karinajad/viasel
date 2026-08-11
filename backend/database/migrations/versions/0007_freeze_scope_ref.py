"""freeze_event.scope_ref — which building or area the freeze covered

`scope='building'` without naming the building is an incomplete record: you couldn't
answer "was C1 frozen?" from the event. Scope also drops `system` in favour of `area`,
so the axis is exactly the project's location legend — design releases by place, and
grouping equipment for one vendor is a sourcing concern (bid packages), not a design gate.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("freeze_event", sa.Column("scope_ref", sa.String(), nullable=True), schema="viasel")


def downgrade() -> None:
    op.drop_column("freeze_event", "scope_ref", schema="viasel")

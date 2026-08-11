"""demand_line.rom_basis + rom_note — which point of the band was taken, and why

The band's mid is a median, and a median is count-weighted by how the corpus happened to
be collected: six distributor rows outvote two direct-from-OEM rows and the "mid" quietly
becomes the distributor route. Departing from it is a judgment, and a judgment with no
stated reason is the thing this record exists to prevent.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("demand_line", sa.Column("rom_basis", sa.String(), nullable=True), schema="viasel")
    op.add_column("demand_line", sa.Column("rom_note", sa.String(), nullable=True), schema="viasel")


def downgrade() -> None:
    op.drop_column("demand_line", "rom_note", schema="viasel")
    op.drop_column("demand_line", "rom_basis", schema="viasel")

"""exhibit_item gains equipment_type_id, building, area — the grain each tab actually needs

Required documents attach to an equipment type, not to every unit of it: "all padmount
transformers need factory test reports" is one row, not twelve. Shipping capacity is stated
per building/area across time, so it carries its own place instead of borrowing one from a
committed line.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exhibit_item", sa.Column("equipment_type_id", sa.Uuid(), nullable=True), schema="viasel")
    op.create_foreign_key(
        "exhibit_item_equipment_type_id_fkey", "exhibit_item", "equipment_type",
        ["equipment_type_id"], ["id"], source_schema="viasel", referent_schema="viasel",
    )
    op.add_column("exhibit_item", sa.Column("building", sa.String(), nullable=True), schema="viasel")
    op.add_column("exhibit_item", sa.Column("area", sa.String(), nullable=True), schema="viasel")


def downgrade() -> None:
    op.drop_column("exhibit_item", "area", schema="viasel")
    op.drop_column("exhibit_item", "building", schema="viasel")
    op.drop_constraint("exhibit_item_equipment_type_id_fkey", "exhibit_item", type_="foreignkey", schema="viasel")
    op.drop_column("exhibit_item", "equipment_type_id", schema="viasel")

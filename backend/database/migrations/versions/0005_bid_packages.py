"""bid packages: sourcing_package + package_line; quotes may target a package

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    # creates sourcing_package + package_line (and the one-active-package index)
    Base.metadata.create_all(bind=op.get_bind())

    # a quote now targets a package OR a single demand line — exactly one of the two
    op.add_column(
        "quote",
        sa.Column("sourcing_package_id", sa.Uuid(), nullable=True),
        schema="viasel",
    )
    op.create_foreign_key(
        "quote_sourcing_package_id_fkey",
        "quote", "sourcing_package",
        ["sourcing_package_id"], ["id"],
        source_schema="viasel", referent_schema="viasel",
    )
    op.alter_column("quote", "demand_line_id", nullable=True, schema="viasel")
    op.create_check_constraint(
        "quote_target_exactly_one",
        "quote",
        "(demand_line_id IS NULL) <> (sourcing_package_id IS NULL)",
        schema="viasel",
    )


def downgrade() -> None:
    op.drop_constraint("quote_target_exactly_one", "quote", type_="check", schema="viasel")
    op.drop_constraint("quote_sourcing_package_id_fkey", "quote", type_="foreignkey", schema="viasel")
    op.drop_column("quote", "sourcing_package_id", schema="viasel")
    op.alter_column("quote", "demand_line_id", nullable=False, schema="viasel")
    op.drop_table("package_line", schema="viasel")
    op.drop_table("sourcing_package", schema="viasel")

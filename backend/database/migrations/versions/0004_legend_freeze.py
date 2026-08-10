"""legend freeze: project.legend_frozen, project_location.active, legend_event

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project",
        sa.Column("legend_frozen", sa.Boolean(), server_default="false", nullable=False),
        schema="viasel",
    )
    op.add_column(
        "project_location",
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        schema="viasel",
    )
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # creates legend_event


def downgrade() -> None:
    op.drop_table("legend_event", schema="viasel")
    op.drop_column("project_location", "active", schema="viasel")
    op.drop_column("project", "legend_frozen", schema="viasel")

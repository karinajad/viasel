"""projects: project + project_location tables

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # checkfirst=True → only new tables


def downgrade() -> None:
    op.drop_table("project_location", schema="viasel")
    op.drop_table("project", schema="viasel")

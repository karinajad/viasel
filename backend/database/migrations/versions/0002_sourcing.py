"""sourcing: quote + scope_line tables

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    # create_all is checkfirst=True — creates only the new quote/scope_line tables
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.drop_table("scope_line", schema="viasel")
    op.drop_table("quote", schema="viasel")

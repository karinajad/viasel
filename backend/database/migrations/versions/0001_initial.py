"""initial: viasel schema + five Phase-1 tables

Revision ID: 0001
Revises:
Create Date: 2026-08-09
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS viasel")
    # single source of truth = app/models.py
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.drop_all(bind=op.get_bind())
    op.execute("DROP SCHEMA IF EXISTS viasel CASCADE")

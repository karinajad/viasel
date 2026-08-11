"""project detail for inference + per-building capacity + accountability

Typed columns, not a JSONB bag: quantity inference queries MW and redundancy, price
inference queries jurisdiction and origin, and spec qualification queries the site
conditions (elevation, ambient, sound) that ruled real bids out on the Cheyenne lot.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

PROJECT_COLS = [
    ("site_code", sa.String()),
    ("buyer_entity", sa.String()),
    ("address", sa.String()),
    ("city", sa.String()),
    ("state", sa.String()),
    ("country", sa.String()),
    ("mw_it", sa.Numeric()),
    ("redundancy", sa.String()),
    ("cooling", sa.String()),
    ("elevation_ft", sa.Integer()),
    ("ambient_max_f", sa.Integer()),
    ("sound_limit_dba", sa.Integer()),
    ("target_energization", sa.Date()),
]
LOCATION_COLS = [("mw_it", sa.Numeric()), ("target_energization", sa.Date())]


def upgrade() -> None:
    for name, kind in PROJECT_COLS:
        op.add_column("project", sa.Column(name, kind, nullable=True), schema="viasel")
    for name, kind in LOCATION_COLS:
        op.add_column("project_location", sa.Column(name, kind, nullable=True), schema="viasel")

    import app.models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # creates project_contact


def downgrade() -> None:
    op.drop_table("project_contact", schema="viasel")
    for name, _ in LOCATION_COLS:
        op.drop_column("project_location", name, schema="viasel")
    for name, _ in PROJECT_COLS:
        op.drop_column("project", name, schema="viasel")

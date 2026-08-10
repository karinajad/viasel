"""Phase-1 data model — the five canonical tables, in the `viasel` schema.

Physics-only equipment types + executed price corpus + demand lines + freeze/thaw events.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

SCHEMA = "viasel"


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class EquipmentType(Base):
    __tablename__ = "equipment_type"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    design_term: Mapped[str] = mapped_column(String, nullable=False)
    unit_type_code: Mapped[str] = mapped_column(String, nullable=False)
    sub_type: Mapped[str | None] = mapped_column(String)
    natural_denominator: Mapped[str] = mapped_column(String, nullable=False)
    denominator_basis: Mapped[str | None] = mapped_column(String)


class ExecutedScopeLine(Base):
    """Historical executed price corpus the ROM queries (seed data)."""

    __tablename__ = "executed_scope_line"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    equipment_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.equipment_type.id")
    )
    etype: Mapped[str | None] = mapped_column(String)
    spec: Mapped[str | None] = mapped_column(String)
    designation: Mapped[str | None] = mapped_column(String)
    supplier: Mapped[str | None] = mapped_column(String)
    oem: Mapped[str | None] = mapped_column(String)
    qty: Mapped[float | None] = mapped_column(Numeric)
    status: Mapped[str | None] = mapped_column(String)  # Executed | Proposal | ROM (confidence)
    denominator: Mapped[str | None] = mapped_column(String)
    size: Mapped[float | None] = mapped_column(Numeric)
    base_unit: Mapped[float | None] = mapped_column(Numeric)
    services_unit: Mapped[float | None] = mapped_column(Numeric)
    tax_pct: Mapped[float | None] = mapped_column(Numeric)
    normalized: Mapped[float | None] = mapped_column(Numeric)
    allin_reported: Mapped[float | None] = mapped_column(Numeric)
    source_ref: Mapped[str | None] = mapped_column(String)


class DemandLine(Base):
    __tablename__ = "demand_line"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    equipment_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.equipment_type.id")
    )
    spec_attributes: Mapped[dict | None] = mapped_column(JSONB)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    target_building: Mapped[str | None] = mapped_column(String)
    target_area: Mapped[str | None] = mapped_column(String)
    target_position: Mapped[str | None] = mapped_column(String)
    required_by_date: Mapped[date | None] = mapped_column(Date)
    rom_unit_price: Mapped[float | None] = mapped_column(Numeric)
    rom_confidence: Mapped[str | None] = mapped_column(String)
    rom_comparables_count: Mapped[int | None] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"), nullable=False)
    state: Mapped[str] = mapped_column(
        String, default="drafted", server_default=text("'drafted'"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FreezeEvent(Base):
    __tablename__ = "freeze_event"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    scope: Mapped[str] = mapped_column(String, nullable=False)  # project | building | system
    demand_line_ids: Mapped[list | None] = mapped_column(JSONB)
    actor: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ThawEvent(Base):
    __tablename__ = "thaw_event"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    freeze_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.freeze_event.id"), nullable=False
    )
    triggering_odd_id: Mapped[str | None] = mapped_column(String)
    released_line_ids: Mapped[list | None] = mapped_column(JSONB)
    actor: Mapped[str | None] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

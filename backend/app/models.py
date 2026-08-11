"""Phase-1 data model — the five canonical tables, in the `viasel` schema.

Physics-only equipment types + executed price corpus + demand lines + freeze/thaw events.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
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
    # the scope axis IS the project's location legend — design releases by place, and a
    # commercial grouping (which lots go to which vendor) belongs to sourcing, not to this gate
    scope: Mapped[str] = mapped_column(String, nullable=False)  # project | building | area
    scope_ref: Mapped[str | None] = mapped_column(String)  # which building/area; null for project
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


class SourcingPackage(Base):
    """A bid package — one equipment type at one size, bought as a lot across the project.

    Pooling is strict: every line in a package shares (type, denominator, size), so a single
    vendor price per unit levels against every line in it without any arithmetic.
    """

    __tablename__ = "sourcing_package"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)  # PKG-01, PKG-02 … per project
    equipment_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.equipment_type.id")
    )
    type_query: Mapped[str] = mapped_column(String, nullable=False)
    denominator: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[float] = mapped_column(Numeric, nullable=False)
    state: Mapped[str] = mapped_column(
        String, default="open", server_default=text("'open'"), nullable=False
    )  # open | awarded | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PackageLine(Base):
    """Which demand lines a package covers. Soft-deleted, so re-packaging keeps its history."""

    __tablename__ = "package_line"
    __table_args__ = (
        # a unit can be in only one open package at a time — no double-sourcing
        Index(
            "package_line_one_active",
            "demand_line_id",
            unique=True,
            postgresql_where=text("active"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    sourcing_package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.sourcing_package.id"), nullable=False
    )
    demand_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.demand_line.id"), nullable=False
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Quote(Base):
    """A candidate supply — against a bid package, or against a single frozen demand line."""

    __tablename__ = "quote"
    __table_args__ = (
        CheckConstraint(
            "(demand_line_id IS NULL) <> (sourcing_package_id IS NULL)",
            name="quote_target_exactly_one",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    demand_line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.demand_line.id")
    )
    sourcing_package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.sourcing_package.id")
    )
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    oem: Mapped[str | None] = mapped_column(String)
    unit_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    lead_time_weeks: Mapped[int | None] = mapped_column(Integer)
    denominator: Mapped[str | None] = mapped_column(String)
    size: Mapped[float | None] = mapped_column(Numeric)
    terms_note: Mapped[str | None] = mapped_column(String)

    # cost layers — `unit_price` above is equipment only. Services/freight/discount are per
    # unit; `one_time_cost` is per ORDER (factory witness test, owner's training) and so
    # amortizes over the lot — which is why an all-in unit price depends on the quantity.
    services_unit: Mapped[float | None] = mapped_column(Numeric)
    freight_unit: Mapped[float | None] = mapped_column(Numeric)
    discount_unit: Mapped[float | None] = mapped_column(Numeric)  # positive = subtracted
    one_time_cost: Mapped[float | None] = mapped_column(Numeric)

    state: Mapped[str] = mapped_column(
        String, default="received", server_default=text("'received'"), nullable=False
    )  # received | selected | declined
    disposition_reason: Mapped[str | None] = mapped_column(String)  # why a bid was ruled out
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScopeLine(Base):
    """Committed supply — created at award, matched to the demand line."""

    __tablename__ = "scope_line"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    demand_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.demand_line.id"), nullable=False
    )
    quote_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA}.quote.id"))
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_code: Mapped[str | None] = mapped_column(String)
    change_type: Mapped[str] = mapped_column(
        String, default="baseline", server_default=text("'baseline'"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "project"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    legend_frozen: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectLocation(Base):
    """A building/area codifier for a project — feeds the location dropdowns."""

    __tablename__ = "project_location"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.project.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)  # e.g. C1, DH3
    kind: Mapped[str] = mapped_column(String, default="building", server_default=text("'building'"), nullable=False)
    label: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegendEvent(Base):
    """Permanent audit of a project's legend freeze/thaw — the crosswalk history."""

    __tablename__ = "legend_event"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.project.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # freeze | thaw
    reason: Mapped[str | None] = mapped_column(String)
    actor: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

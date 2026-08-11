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
    # long-lead equipment: the items whose lead time drives what dates you can promise a
    # customer, so they get bought before the rest — often before there is a customer at all
    is_lle: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    rom_unit_price: Mapped[float | None] = mapped_column(Numeric)
    rom_confidence: Mapped[str | None] = mapped_column(String)
    rom_comparables_count: Mapped[int | None] = mapped_column(Integer)
    # which point of the band was taken, and why. A median is count-weighted by how the
    # corpus happened to be collected, so departing from it is a judgment worth recording.
    rom_basis: Mapped[str | None] = mapped_column(String)  # mid | low | high | route:<name>
    rom_note: Mapped[str | None] = mapped_column(String)
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
    vendor: Mapped[str] = mapped_column(String, nullable=False)  # as typed, kept verbatim
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA}.vendor.id"))
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
    agreement_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA}.agreement.id"))
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
    """A project, and the facts about it that let history be inferred onto it.

    These are typed columns rather than a free-form bag because inference has to query
    them: quantity suggestions need MW and topology, price needs jurisdiction and origin,
    and spec qualification needs the site conditions that ruled real bids out.
    """

    __tablename__ = "project"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    legend_frozen: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)

    # identity and where the site is
    site_code: Mapped[str | None] = mapped_column(String)  # e.g. DTW01
    # legal name of the company assigned to this project — the name that appears on the PO
    buyer_entity: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)  # drives tax jurisdiction
    country: Mapped[str | None] = mapped_column(String)

    # capacity and topology — the denominators quantity inference needs. Units per MW is
    # meaningless without the redundancy: 2N doubles the electrical count for the same load.
    mw_it: Mapped[float | None] = mapped_column(Numeric)
    redundancy: Mapped[str | None] = mapped_column(String)  # N | N+1 | 2N | 2N+1
    cooling: Mapped[str | None] = mapped_column(String)  # air-cooled | liquid | hybrid

    # site conditions — these qualified and disqualified real bids, so they belong on the
    # record rather than in someone's head at RFQ time
    elevation_ft: Mapped[int | None] = mapped_column(Integer)
    ambient_max_f: Mapped[int | None] = mapped_column(Integer)
    sound_limit_dba: Mapped[int | None] = mapped_column(Integer)

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
    mw_it: Mapped[float | None] = mapped_column(Numeric)  # this building's share of the load
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


class ProjectContact(Base):
    """Who is accountable and responsible, by function.

    Recorded, not enforced: there is no user or role model behind this yet, so this is a
    signature ledger rather than a permission system. Saying so is the point — the award
    memo and the COAP log both prove the ledger is what people actually chase.
    """

    __tablename__ = "project_contact"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.project.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    function: Mapped[str] = mapped_column(String, nullable=False)  # procurement · electrical design · …
    accountability: Mapped[str] = mapped_column(
        String, default="responsible", server_default=text("'responsible'"), nullable=False
    )  # accountable | responsible | consulted | informed
    org: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vendor(Base):
    """A vendor as a record, not a typed string.

    Free-typed vendor names make "Eaton" and "Eaton Corp" two different vendors, which is
    why vendor reliability (spec §11) can never accumulate: you cannot compare a quoted
    lead time against an actual delivery if the two rows don't agree on who the vendor was.

    The supply-chain fields are the ones the award form asks for, and they matter because
    the executed corpus shows the route — distributor vs. direct, and which OEM behind it —
    driving the price spread more than anything else.
    """

    __tablename__ = "vendor"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String)  # e.g. EAT, PH — their own convention
    role: Mapped[str] = mapped_column(
        String, default="supplier", server_default=text("'supplier'"), nullable=False
    )  # oem | distributor | integrator | supplier
    oem_names: Mapped[list | None] = mapped_column(JSONB)  # who actually manufactures

    factory_country: Mapped[str | None] = mapped_column(String)
    factory_location: Mapped[str | None] = mapped_column(String)
    integration_location: Mapped[str | None] = mapped_column(String)
    sub_supplier: Mapped[str | None] = mapped_column(String)

    status: Mapped[str] = mapped_column(
        String, default="approved", server_default=text("'approved'"), nullable=False
    )  # prospect | approved | preferred | hold | disqualified
    status_note: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorContact(Base):
    """Who to talk to at a vendor. The award memo names people, so the record should too."""

    __tablename__ = "vendor_contact"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.vendor.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Agreement(Base):
    """The instrument that commits supply — and the thing exhibits are generated from.

    Contract value is never stored. It is the sum of the scope lines the agreement covers,
    so the document and the record cannot disagree about what was bought: there is only one
    number and it is derived. An exhibit is a view of this, not a file attached to it.
    """

    __tablename__ = "agreement"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA}.vendor.id"))
    vendor_name: Mapped[str] = mapped_column(String, nullable=False)  # as committed, verbatim
    code: Mapped[str] = mapped_column(String, nullable=False)  # e.g. MIT-EAT-002
    agreement_type: Mapped[str] = mapped_column(
        String, default="purchase", server_default=text("'purchase'"), nullable=False
    )  # purchase | integration
    # snapshotted at issue: the buyer entity on an executed document must not silently
    # change because someone later edited the project
    buyer_entity: Mapped[str | None] = mapped_column(String)
    # our own side only. Viasel authors the exhibit data and hands it over; whether the
    # instrument was signed is a fact about the executed document, not a state we perform.
    state: Mapped[str] = mapped_column(
        String, default="drafted", server_default=text("'drafted'"), nullable=False
    )  # drafted | released | withdrawn
    released_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExecutedAgreement(Base):
    """The signed instrument, as held — not as owned.

    The agreement is executed wherever the client already executes agreements. Viasel's job
    is to take the executed version back, record where it lives, and reconcile it field by
    field against the exhibit data it generated. That reconciliation is the point: a quantity
    trimmed in negotiation or a price retyped by hand never becomes a formal amendment, and
    is invisible to everyone until the two versions are compared.
    """

    __tablename__ = "executed_agreement"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.agreement.id"), nullable=False
    )
    source_system: Mapped[str] = mapped_column(String, nullable=False)  # where it actually lives
    external_document_ref: Mapped[str | None] = mapped_column(String)
    execution_date: Mapped[date | None] = mapped_column(Date)

    # what the signed document says, as read off it — deliberately separate from what the
    # record generated, because the whole exercise is comparing the two
    stated_po_number: Mapped[str | None] = mapped_column(String)
    stated_buyer_entity: Mapped[str | None] = mapped_column(String)
    stated_vendor_name: Mapped[str | None] = mapped_column(String)
    stated_total_qty: Mapped[int | None] = mapped_column(Integer)
    stated_contract_value: Mapped[float | None] = mapped_column(Numeric)

    reconciliation_status: Mapped[str] = mapped_column(
        String, default="pending", server_default=text("'pending'"), nullable=False
    )  # pending | matched | diverged
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retrieved_by: Mapped[str | None] = mapped_column(String)


class FieldDivergence(Base):
    """One field where the executed document and the record disagree.

    Flagged, never auto-corrected. Silently adopting the document's number would destroy the
    only evidence that a change happened outside the record.
    """

    __tablename__ = "field_divergence"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    executed_agreement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.executed_agreement.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    generated_value: Mapped[str | None] = mapped_column(String)
    executed_value: Mapped[str | None] = mapped_column(String)
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_by: Mapped[str | None] = mapped_column(String)
    resolution_note: Mapped[str | None] = mapped_column(String)


class ExhibitItem(Base):
    """A line of an exhibit the record can't derive — entered per agreement, per vendor.

    Cover sheet, equipment list and legend fall out of the record. The rest is contract-time
    content: what's in the box, what spares come with it, when each tranche lands, what
    documents are owed and at which gate. Every row can point at the scope line it belongs
    to, which is what ties an exhibit back to the demand that was assigned at sourcing.
    """

    __tablename__ = "exhibit_item"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = _pk()
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.agreement.id"), nullable=False
    )
    # delivery_schedule | spare_parts | bill_of_materials | shipping_capacity | required_documents
    exhibit: Mapped[str] = mapped_column(String, nullable=False)
    # the committed line this row belongs to; null for rows that cover the whole agreement
    scope_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA}.scope_line.id"))
    # required documents usually attach to an equipment TYPE — "every padmount needs factory
    # test reports" — not to each unit. Either grain is allowed; the entry toggles between them.
    equipment_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.equipment_type.id")
    )
    # shipping capacity is stated per place across time, so it carries its own place rather
    # than borrowing one from a line
    building: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)

    description: Mapped[str] = mapped_column(String, nullable=False)
    qty: Mapped[int | None] = mapped_column(Integer)
    unit_price: Mapped[float | None] = mapped_column(Numeric)
    due_date: Mapped[date | None] = mapped_column(Date)
    # for required documents: which lifecycle gate the document is owed at. "prior to final
    # payment" is the withholding lever, so the gate is the part that has teeth.
    gate: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

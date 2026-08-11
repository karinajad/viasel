import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

TYPES = ("purchase", "integration")
STATES = ("drafted", "released", "withdrawn")


class AgreementCreate(BaseModel):
    """Raise an agreement from awarded packages. The scope comes from the record, not typed."""

    project_id: str
    package_ids: list[uuid.UUID]
    code: str | None = None  # defaults to {PROJECT}-{VENDOR}-{seq}, their own convention
    agreement_type: str = "purchase"


class AgreementRelease(BaseModel):
    """Hand the exhibit data over for signature. Signing happens elsewhere."""

    released_date: date | None = None


class ExecutedAgreementCreate(BaseModel):
    """The signed version, as read off it. Every stated field is optional — a blank means
    "not read from the document", which is a different claim from "it disagrees"."""

    source_system: str  # eBuilder · Procore · Textura · wherever it actually lives
    external_document_ref: str | None = None
    execution_date: date | None = None
    stated_po_number: str | None = None
    stated_buyer_entity: str | None = None
    stated_vendor_name: str | None = None
    stated_total_qty: int | None = None
    stated_contract_value: float | None = None
    retrieved_by: str | None = "web"


class ExecutedAgreementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_system: str
    external_document_ref: str | None
    execution_date: date | None
    stated_po_number: str | None
    stated_buyer_entity: str | None
    stated_vendor_name: str | None
    stated_total_qty: int | None
    stated_contract_value: float | None
    reconciliation_status: str
    retrieved_at: datetime
    retrieved_by: str | None


class FieldDivergenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    field_name: str
    generated_value: str | None
    executed_value: str | None
    resolution_note: str | None


class ReconciliationRead(BaseModel):
    executed: ExecutedAgreementRead
    divergences: list[FieldDivergenceRead]


class AgreementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: str
    code: str
    vendor_id: uuid.UUID | None
    vendor_name: str
    agreement_type: str
    buyer_entity: str | None
    state: str
    released_date: date | None
    created_at: datetime

    line_count: int = 0
    total_qty: int = 0
    contract_value: float = 0.0  # derived, never stored — Σ(effective scope lines)
    package_ids: list[uuid.UUID] = []  # the lots this instrument commits
    package_codes: list[str] = []


class CoverSheet(BaseModel):
    """Exhibit cover — parties and identity, every field already on the record."""

    po_number: str
    date_of_issue: date | None
    site_code: str | None
    project_name: str
    project_address: str | None
    buyer_entity: str | None
    vendor_name: str
    vendor_code: str | None
    vendor_contacts: list[str]


class EquipmentRow(BaseModel):
    """One line of Exhibit A, in their own column shape."""

    design_term: str | None
    equipment_spec: str | None
    vendor_description: str | None
    building: str | None
    area: str | None
    qty: int
    unit_price: float
    extended_price: float
    lead_time_weeks: int | None
    oem: str | None


class LegendEntry(BaseModel):
    kind: str  # campus | building | area
    code: str
    description: str | None


EXHIBITS = (
    "delivery_schedule", "spare_parts", "bill_of_materials",
    "shipping_capacity", "required_documents",
)
# their Schedule D lever: a document owed "prior to final payment" is retainage with teeth
GATES = (
    "prior to fabrication release", "prior to factory witness test", "prior to shipment",
    "prior to delivery", "prior to commissioning", "prior to final payment",
)


class ExhibitItemCreate(BaseModel):
    exhibit: str
    description: str
    scope_line_id: uuid.UUID | None = None  # the committed line this row covers
    equipment_type_id: uuid.UUID | None = None  # documents usually attach here instead
    building: str | None = None  # shipping capacity is stated per place
    area: str | None = None
    qty: int | None = None
    unit_price: float | None = None
    due_date: date | None = None
    gate: str | None = None
    note: str | None = None


class ExhibitItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    exhibit: str
    scope_line_id: uuid.UUID | None
    equipment_type_id: uuid.UUID | None
    building: str | None
    area: str | None
    description: str
    qty: int | None
    unit_price: float | None
    due_date: date | None
    gate: str | None
    note: str | None


class LineCoverage(BaseModel):
    """How much of a committed line the delivery schedule accounts for."""

    scope_line_id: uuid.UUID
    label: str  # e.g. "Padmount Transformer 5000kVA · C1 · C1-DH3"
    committed_qty: int
    scheduled_qty: int
    remaining_qty: int


class CommittedLine(BaseModel):
    """A committed line, as something to attach exhibit content to."""

    scope_line_id: uuid.UUID
    label: str
    equipment_type_id: uuid.UUID | None
    design_term: str | None
    building: str | None
    area: str | None
    qty: int
    unit_price: float


class TypeOption(BaseModel):
    """An equipment type on this agreement — the grain documents usually attach at."""

    equipment_type_id: uuid.UUID | None
    label: str
    unit_count: int


class ExhibitSet(BaseModel):
    """The exhibits, generated. Tabs the record can't fill yet are named rather than blanked,
    because a blank in an executed exhibit reads as "nothing required"."""

    agreement: AgreementRead
    cover_sheet: CoverSheet
    equipment_list: list[EquipmentRow]
    legend: list[LegendEntry]
    # entered content, keyed by exhibit — the tabs the record can't derive
    items: dict[str, list[ExhibitItemRead]]
    # per committed line: how much of it the delivery schedule has actually accounted for
    delivery_coverage: list[LineCoverage]
    # what exhibit content can be attached to: the units allocated to this vendor at sourcing
    committed_lines: list[CommittedLine]
    equipment_types: list[TypeOption]
    # ROJ dates already confirmed on the delivery schedule; shipping capacity locks to these
    roj_dates: list[date]

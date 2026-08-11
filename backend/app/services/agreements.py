"""Agreements — and the exhibits that are views of them.

An exhibit is generated from the record, never authored by a counterparty and never a file
attached to an agreement. That is the whole mechanism: if the document is a view, a
placeholder cannot survive execution because there is nothing to leave blank, and the
executed version can later be reconciled field-by-field against what was generated.
"""

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Agreement,
    DemandLine,
    EquipmentType,
    ExecutedAgreement,
    ExhibitItem,
    FieldDivergence,
    Project,
    ProjectLocation,
    Quote,
    ScopeLine,
    SourcingPackage,
    Vendor,
    VendorContact,
)
from app.schemas.agreement import (
    EXHIBITS,
    GATES,
    STATES,
    TYPES,
    AgreementRead,
    CommittedLine,
    CoverSheet,
    EquipmentRow,
    ExecutedAgreementRead,
    ExhibitItemRead,
    ExhibitSet,
    FieldDivergenceRead,
    LegendEntry,
    LineCoverage,
    ReconciliationRead,
    TypeOption,
)

DRAFTED, RELEASED, WITHDRAWN = STATES

DELIVERY = "delivery_schedule"


class AgreementError(Exception):
    """An agreement rule was broken — surfaced as 409."""


def _f(x: object, default: float = 0.0) -> float:
    return float(x) if x is not None else default  # type: ignore[arg-type]


def agreement_lines(session: Session, ag: Agreement) -> list[ScopeLine]:
    """The committed lines, in a stable order.

    Deliberately deterministic: this is the order Exhibit A prints in, and a document whose
    line order shifts between renders is not the same document.
    """
    lines = list(session.scalars(select(ScopeLine).where(ScopeLine.agreement_id == ag.id)))
    places = {
        sl.id: (session.get(DemandLine, sl.demand_line_id) if sl.demand_line_id else None)
        for sl in lines
    }

    def key(sl: ScopeLine) -> tuple[str, str, int, str]:
        dl = places[sl.id]
        return (
            (dl.target_building if dl and dl.target_building else "~"),
            (dl.target_area if dl and dl.target_area else ""),
            -sl.qty,  # the bigger tranche first within a place
            str(sl.id),  # last resort, so the order never wobbles
        )

    return sorted(lines, key=key)


def _next_code(session: Session, project_id: str, vendor_name: str, vendor_code: str | None) -> str:
    """Their convention: {PROJECT}-{VENDOR}-{seq}, e.g. MIT-EAT-002."""
    n = len(list(session.scalars(select(Agreement.id).where(Agreement.project_id == project_id))))
    proj = "".join(c for c in project_id.upper() if c.isalnum())[:3] or "PRJ"
    ven = (vendor_code or "".join(c for c in vendor_name.upper() if c.isalnum())[:3] or "VEN")[:4]
    return f"{proj}-{ven}-{n + 1:03d}"


def create_agreement(
    session: Session,
    project_id: str,
    package_ids: Sequence[uuid.UUID],
    *,
    code: str | None = None,
    agreement_type: str = "purchase",
) -> Agreement:
    """Raise an agreement over awarded packages. One vendor — an instrument has one counterparty."""
    if agreement_type not in TYPES:
        raise AgreementError(f"agreement type must be one of {', '.join(TYPES)}")
    if not package_ids:
        raise AgreementError("an agreement needs at least one awarded package")

    packages = list(
        session.scalars(select(SourcingPackage).where(SourcingPackage.id.in_(package_ids)))
    )
    if len(packages) != len(set(package_ids)):
        raise AgreementError("package not found")
    for pkg in packages:
        if pkg.project_id != project_id:
            raise AgreementError(f"{pkg.code} belongs to another project")
        if pkg.state != "awarded":
            raise AgreementError(f"{pkg.code} is {pkg.state} — only an awarded lot can be committed")

    lines = list(
        session.scalars(
            select(ScopeLine)
            .join(Quote, Quote.id == ScopeLine.quote_id)
            .where(Quote.sourcing_package_id.in_([p.id for p in packages]))
        )
    )
    if not lines:
        raise AgreementError("those packages have no committed scope lines")
    already = [sl for sl in lines if sl.agreement_id is not None]
    if already:
        raise AgreementError(
            f"{len(already)} of those scope lines are already on another agreement"
        )

    vendors = {sl.vendor for sl in lines}
    if len(vendors) > 1:
        # split award will change this; today one instrument means one counterparty
        raise AgreementError(f"those packages were awarded to different vendors: {', '.join(sorted(vendors))}")
    vendor_name = next(iter(vendors))
    vendor = session.scalar(select(Vendor).where(Vendor.name == vendor_name))

    proj = session.scalar(select(Project).where(Project.name == project_id))
    ag = Agreement(
        project_id=project_id,
        vendor_id=vendor.id if vendor else None,
        vendor_name=vendor_name,
        code=code or _next_code(session, project_id, vendor_name, vendor.code if vendor else None),
        agreement_type=agreement_type,
        buyer_entity=proj.buyer_entity if proj else None,
    )
    session.add(ag)
    session.flush()
    for sl in lines:
        sl.agreement_id = ag.id
    session.flush()
    return ag


def transition(session: Session, ag: Agreement, to: str, **dates: object) -> Agreement:
    """drafted → released → (withdrawn).

    There is no "executed" state here on purpose. Releasing is something Viasel does — the
    exhibit data is handed over for signature. Execution happens in whatever system the
    client signs in, and comes back as an ExecutedAgreement rather than as a state we set.
    """
    allowed = {DRAFTED: {RELEASED, WITHDRAWN}, RELEASED: {WITHDRAWN}, WITHDRAWN: set()}
    if to not in allowed.get(ag.state, set()):
        raise AgreementError(f"an agreement cannot go {ag.state} → {to}")
    ag.state = to
    for field, value in dates.items():
        if value is not None:
            setattr(ag, field, value)
    session.flush()
    return ag


def _norm(x: object) -> str | None:
    if x is None:
        return None
    if isinstance(x, float | int):
        return f"{float(x):.2f}"
    return str(x).strip() or None


def register_executed(
    session: Session,
    ag: Agreement,
    *,
    source_system: str,
    external_document_ref: str | None = None,
    execution_date: object = None,
    stated_po_number: str | None = None,
    stated_buyer_entity: str | None = None,
    stated_vendor_name: str | None = None,
    stated_total_qty: int | None = None,
    stated_contract_value: float | None = None,
    retrieved_by: str | None = None,
) -> ExecutedAgreement:
    """Take the signed version back and compare it, field by field, with what we generated.

    Divergence is recorded and never applied. A quantity trimmed during negotiation or a
    price retyped by hand is real, but adopting it silently would erase the only evidence
    that it happened outside the record.
    """
    if ag.state != RELEASED:
        raise AgreementError(
            f"{ag.code} is {ag.state} — release the exhibit data before registering a signed version"
        )
    if not source_system:
        raise AgreementError("say which system holds the executed document")
    if session.scalar(select(ExecutedAgreement).where(ExecutedAgreement.agreement_id == ag.id)):
        raise AgreementError(f"{ag.code} already has an executed version on record")

    ours = read(session, ag)
    ex = ExecutedAgreement(
        agreement_id=ag.id, source_system=source_system,
        external_document_ref=external_document_ref, execution_date=execution_date,
        stated_po_number=stated_po_number, stated_buyer_entity=stated_buyer_entity,
        stated_vendor_name=stated_vendor_name, stated_total_qty=stated_total_qty,
        stated_contract_value=stated_contract_value, retrieved_by=retrieved_by,
    )
    session.add(ex)
    session.flush()

    # only fields the signed document actually stated — a blank is "not read off it", which
    # is a different claim from "it disagrees"
    checks = (
        ("po_number", ours.code, stated_po_number),
        ("buyer_entity", ag.buyer_entity, stated_buyer_entity),
        ("vendor_name", ag.vendor_name, stated_vendor_name),
        ("total_qty", ours.total_qty, stated_total_qty),
        ("contract_value", ours.contract_value, stated_contract_value),
    )
    diverged = 0
    for field, generated, executed in checks:
        if executed is None:
            continue
        g, e = _norm(generated), _norm(executed)
        if g != e:
            diverged += 1
            session.add(
                FieldDivergence(
                    executed_agreement_id=ex.id, field_name=field,
                    generated_value=g, executed_value=e,
                )
            )
    ex.reconciliation_status = "diverged" if diverged else "matched"
    session.flush()
    return ex


def reconciliation(session: Session, ag: Agreement) -> ReconciliationRead | None:
    ex = session.scalar(select(ExecutedAgreement).where(ExecutedAgreement.agreement_id == ag.id))
    if ex is None:
        return None
    divergences = list(
        session.scalars(
            select(FieldDivergence).where(FieldDivergence.executed_agreement_id == ex.id)
        )
    )
    return ReconciliationRead(
        executed=ExecutedAgreementRead.model_validate(ex),
        divergences=[FieldDivergenceRead.model_validate(d) for d in divergences],
    )


def agreement_packages(session: Session, ag: Agreement) -> list[SourcingPackage]:
    """The lots this instrument commits, reached through the winning quotes."""
    return list(
        session.scalars(
            select(SourcingPackage)
            .join(Quote, Quote.sourcing_package_id == SourcingPackage.id)
            .join(ScopeLine, ScopeLine.quote_id == Quote.id)
            .where(ScopeLine.agreement_id == ag.id)
            .distinct()
            .order_by(SourcingPackage.code)
        )
    )


def read(session: Session, ag: Agreement) -> AgreementRead:
    lines = agreement_lines(session, ag)
    packages = agreement_packages(session, ag)
    return AgreementRead(
        **{c.name: getattr(ag, c.name) for c in Agreement.__table__.columns},
        line_count=len(lines),
        total_qty=sum(sl.qty for sl in lines),
        # derived, so the document and the record can never hold two different totals
        contract_value=round(sum(_f(sl.unit_price) * sl.qty for sl in lines), 2),
        package_ids=[p.id for p in packages],
        package_codes=[p.code for p in packages],
    )


def exhibits(session: Session, ag: Agreement) -> ExhibitSet:
    """Generate the exhibit set from the record."""
    proj = session.scalar(select(Project).where(Project.name == ag.project_id))
    vendor = session.get(Vendor, ag.vendor_id) if ag.vendor_id else None
    contacts = (
        list(
            session.scalars(
                select(VendorContact).where(
                    VendorContact.vendor_id == vendor.id, VendorContact.active.is_(True)
                )
            )
        )
        if vendor
        else []
    )

    cover = CoverSheet(
        po_number=ag.code,
        date_of_issue=ag.released_date,
        site_code=proj.site_code if proj else None,
        project_name=ag.project_id,
        project_address=", ".join(
            x for x in ((proj.address if proj else None), (proj.city if proj else None),
                        (proj.state if proj else None)) if x
        ) or None,
        buyer_entity=ag.buyer_entity,
        vendor_name=ag.vendor_name,
        vendor_code=vendor.code if vendor else None,
        vendor_contacts=[
            " · ".join(x for x in (c.name, c.title, c.email) if x) for c in contacts
        ],
    )

    rows = []
    for sl in agreement_lines(session, ag):
        dl = session.get(DemandLine, sl.demand_line_id)
        quote = session.get(Quote, sl.quote_id) if sl.quote_id else None
        attrs = (dl.spec_attributes or {}) if dl else {}
        etype = session.get(EquipmentType, dl.equipment_type_id) if dl and dl.equipment_type_id else None
        rows.append(
            EquipmentRow(
                design_term=etype.design_term if etype else str(attrs.get("type_query") or "") or None,
                equipment_spec=str(attrs.get("sub") or attrs.get("size") or "") or None,
                vendor_description=str(attrs.get("type_query") or "") or None,
                building=dl.target_building if dl else None,
                area=dl.target_area if dl else None,
                qty=sl.qty,
                unit_price=round(_f(sl.unit_price), 2),
                extended_price=round(_f(sl.unit_price) * sl.qty, 2),
                lead_time_weeks=quote.lead_time_weeks if quote else None,
                oem=quote.oem if quote else None,
            )
        )

    legend: list[LegendEntry] = []
    if proj:
        if proj.site_code:
            legend.append(LegendEntry(kind="campus", code=proj.site_code, description=proj.name))
        for loc in session.scalars(
            select(ProjectLocation)
            .where(ProjectLocation.project_id == proj.id, ProjectLocation.active.is_(True))
            .order_by(ProjectLocation.kind, ProjectLocation.code)
        ):
            legend.append(LegendEntry(kind=loc.kind, code=loc.code, description=loc.label))

    items: dict[str, list[ExhibitItemRead]] = {e: [] for e in EXHIBITS}
    for item in exhibit_items(session, ag):
        items[item.exhibit].append(ExhibitItemRead.model_validate(item))

    return ExhibitSet(
        agreement=read(session, ag),
        cover_sheet=cover,
        equipment_list=rows,
        legend=legend,
        items=items,
        delivery_coverage=delivery_coverage(session, ag),
        committed_lines=committed_lines(session, ag),
        equipment_types=type_options(session, ag),
        roj_dates=roj_dates(session, ag),
    )


def _line_label(session: Session, sl: ScopeLine) -> str:
    dl = session.get(DemandLine, sl.demand_line_id)
    attrs = (dl.spec_attributes or {}) if dl else {}
    where = " · ".join(
        x for x in ((dl.target_building if dl else None), (dl.target_area if dl else None)) if x
    )
    what = " ".join(
        str(x) for x in (attrs.get("type_query"), attrs.get("sub") or attrs.get("size")) if x
    )
    return " · ".join(x for x in (what, where or "unassigned") if x) or "line"


def exhibit_items(session: Session, ag: Agreement) -> list[ExhibitItem]:
    return list(
        session.scalars(
            select(ExhibitItem)
            .where(ExhibitItem.agreement_id == ag.id, ExhibitItem.active.is_(True))
            .order_by(ExhibitItem.exhibit, ExhibitItem.due_date, ExhibitItem.description)
        )
    )


def add_exhibit_item(
    session: Session,
    ag: Agreement,
    *,
    exhibit: str,
    description: str,
    scope_line_id: uuid.UUID | None = None,
    equipment_type_id: uuid.UUID | None = None,
    building: str | None = None,
    area: str | None = None,
    qty: int | None = None,
    unit_price: float | None = None,
    due_date: object = None,
    vendor_delivery_date: object = None,
    designation: str | None = None,
    gate: str | None = None,
    is_included: bool | None = None,
    is_required: bool | None = None,
    lead_time_weeks: int | None = None,
    note: str | None = None,
) -> ExhibitItem:
    """Enter a line of an exhibit, optionally against the committed line it covers."""
    if exhibit not in EXHIBITS:
        raise AgreementError(f"exhibit must be one of {', '.join(EXHIBITS)} — got '{exhibit}'")
    if gate is not None and gate not in GATES:
        raise AgreementError(f"gate must be one of {', '.join(GATES)}")
    if exhibit == "required_documents" and not gate:
        raise AgreementError(
            "a required document needs the gate it is owed at — a document with no gate has no teeth"
        )

    lines = {sl.id: sl for sl in agreement_lines(session, ag)}
    if scope_line_id is not None and scope_line_id not in lines:
        raise AgreementError("that scope line is not on this agreement")
    existing = exhibit_items(session, ag)

    # spares and a bill of materials describe specific units, so they name the line they
    # belong to — the units allocated to this vendor at sourcing
    if exhibit in ("spare_parts", "bill_of_materials") and scope_line_id is None:
        raise AgreementError(
            f"a {exhibit.replace('_', ' ')} row has to name the committed line it belongs to"
        )

    if exhibit == DELIVERY:
        if not qty or qty < 1:
            raise AgreementError("a delivery schedule row needs a quantity")
        if not due_date:
            raise AgreementError("a delivery schedule row needs its ROJ date")
        # a schedule that promises more units than were bought is wrong on its face, and it
        # is the exhibit the vendor performs against. Scoped per line when a line is named,
        # otherwise across the whole vendor's committed quantity.
        peers = [
            i for i in existing
            if i.exhibit == DELIVERY and (scope_line_id is None or i.scope_line_id == scope_line_id)
        ]
        already = sum(i.qty or 0 for i in peers)
        cap = lines[scope_line_id].qty if scope_line_id else sum(sl.qty for sl in lines.values())
        where = _line_label(session, lines[scope_line_id]) if scope_line_id else f"{ag.code} overall"
        if already + qty > cap:
            raise AgreementError(
                f"that would schedule {already + qty} of {cap} committed units on {where} — "
                f"{cap - already} left to schedule"
            )

    if exhibit == "shipping_capacity":
        # capacity is a rate for a particular thing going to a particular place: a vendor's
        # throughput on transformers is not their throughput on switchgear, and a hall that
        # can take four a month is not the campus that can take twelve
        if not equipment_type_id:
            raise AgreementError("shipping capacity is per equipment type — say which type")
        if not building:
            raise AgreementError("shipping capacity is stated per building — say which one")
        if not due_date:
            raise AgreementError("shipping capacity needs the date the period starts")
        types = {o.equipment_type_id for o in type_options(session, ag)}
        if equipment_type_id not in types:
            raise AgreementError("that equipment type isn't on this agreement")
        confirmed = {i.due_date for i in existing if i.exhibit == DELIVERY and i.due_date}
        if not confirmed:
            raise AgreementError(
                "no ROJ dates on the delivery schedule yet — capacity locks to a confirmed date"
            )
        if due_date not in confirmed:
            raise AgreementError(
                f"{due_date} is not a confirmed ROJ date. Confirmed: "
                + ", ".join(str(d) for d in sorted(confirmed))
            )

    item = ExhibitItem(
        agreement_id=ag.id, exhibit=exhibit, description=description,
        scope_line_id=scope_line_id, equipment_type_id=equipment_type_id,
        building=building, area=area, qty=qty, unit_price=unit_price,
        due_date=due_date, vendor_delivery_date=vendor_delivery_date,
        designation=designation, gate=gate, is_included=is_included,
        is_required=is_required, lead_time_weeks=lead_time_weeks, note=note,
    )
    session.add(item)
    session.flush()
    return item


def update_exhibit_item(
    session: Session, ag: Agreement, item_id: uuid.UUID, patch: dict[str, Any]
) -> ExhibitItem:
    """Change a row in place. The delivery cap still holds when a quantity moves."""
    item = session.get(ExhibitItem, item_id)
    if item is None or item.agreement_id != ag.id or not item.active:
        raise AgreementError("that exhibit line is not on this agreement")

    if item.exhibit == DELIVERY and "qty" in patch and patch["qty"] is not None:
        lines = {sl.id: sl for sl in agreement_lines(session, ag)}
        peers = [
            i for i in exhibit_items(session, ag)
            if i.exhibit == DELIVERY and i.id != item.id
            and (item.scope_line_id is None or i.scope_line_id == item.scope_line_id)
        ]
        already = sum(i.qty or 0 for i in peers)
        cap = (
            lines[item.scope_line_id].qty if item.scope_line_id and item.scope_line_id in lines
            else sum(sl.qty for sl in lines.values())
        )
        wanted = int(patch["qty"])
        if already + wanted > cap:
            raise AgreementError(
                f"that would schedule {already + wanted} of {cap} committed units — "
                f"{cap - already} available on this line"
            )

    for field, value in patch.items():
        setattr(item, field, value)
    session.flush()
    return item


def remove_exhibit_item(session: Session, ag: Agreement, item_id: uuid.UUID) -> None:
    item = session.get(ExhibitItem, item_id)
    if item is None or item.agreement_id != ag.id or not item.active:
        raise AgreementError("that exhibit line is not on this agreement")
    item.active = False  # soft — what an exhibit said at a point in time stays recoverable
    session.flush()


def committed_lines(session: Session, ag: Agreement) -> list[CommittedLine]:
    """The units allocated to this vendor at sourcing — what exhibit content attaches to."""
    out = []
    for sl in agreement_lines(session, ag):
        dl = session.get(DemandLine, sl.demand_line_id)
        etype = (
            session.get(EquipmentType, dl.equipment_type_id)
            if dl and dl.equipment_type_id else None
        )
        out.append(
            CommittedLine(
                scope_line_id=sl.id,
                label=_line_label(session, sl),
                equipment_type_id=etype.id if etype else None,
                design_term=etype.design_term if etype else None,
                building=dl.target_building if dl else None,
                area=dl.target_area if dl else None,
                qty=sl.qty,
                unit_price=round(_f(sl.unit_price), 2),
            )
        )
    return out


def type_options(session: Session, ag: Agreement) -> list[TypeOption]:
    """Equipment types on this agreement — the grain required documents usually attach at."""
    seen: dict[uuid.UUID | None, TypeOption] = {}
    for cl in committed_lines(session, ag):
        key = cl.equipment_type_id
        if key not in seen:
            label = cl.label.split(" · ")[0] if cl.label else "untyped"
            seen[key] = TypeOption(equipment_type_id=key, label=label, unit_count=0)
        seen[key].unit_count += cl.qty
    return sorted(seen.values(), key=lambda o: o.label)


def roj_dates(session: Session, ag: Agreement) -> list[date]:
    return sorted(
        {i.due_date for i in exhibit_items(session, ag) if i.exhibit == DELIVERY and i.due_date}
    )


def delivery_coverage(session: Session, ag: Agreement) -> list[LineCoverage]:
    """Per committed line, how much of it the delivery schedule accounts for."""
    items = [i for i in exhibit_items(session, ag) if i.exhibit == DELIVERY]
    out = []
    for sl in agreement_lines(session, ag):
        scheduled = sum(i.qty or 0 for i in items if i.scope_line_id == sl.id)
        out.append(
            LineCoverage(
                scope_line_id=sl.id,
                label=_line_label(session, sl),
                committed_qty=sl.qty,
                scheduled_qty=scheduled,
                remaining_qty=sl.qty - scheduled,
            )
        )
    return out


def list_agreements(session: Session, project_id: str) -> list[AgreementRead]:
    return [
        read(session, ag)
        for ag in session.scalars(
            select(Agreement)
            .where(Agreement.project_id == project_id)
            .order_by(Agreement.code)
        )
    ]

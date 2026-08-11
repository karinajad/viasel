import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import Quote, Vendor, VendorContact
from app.schemas.vendor import (
    BIDDABLE,
    ROLES,
    STATUSES,
    VendorContactRead,
    VendorContactWrite,
    VendorDetail,
    VendorPatch,
    VendorRead,
    VendorWrite,
)

router = APIRouter(prefix="/vendors", tags=["vendors"], dependencies=[Depends(require_token)])


def _vendor(session: Session, vendor_id: uuid.UUID) -> Vendor:
    v = session.get(Vendor, vendor_id)
    if v is None or not v.active:
        raise HTTPException(status_code=404, detail="vendor not found")
    return v


def _one_of(value: str | None, allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=400, detail=f"{field} must be one of {', '.join(allowed)} — got '{value}'"
        )


@router.get("", response_model=list[VendorRead])
def list_vendors(
    biddable_only: bool = False, session: Session = Depends(get_session)
) -> list[Vendor]:
    """The vendor roster. `biddable_only` drops the ones you can't actually buy from."""
    stmt = select(Vendor).where(Vendor.active.is_(True))
    if biddable_only:
        stmt = stmt.where(Vendor.status.in_(BIDDABLE))
    return list(session.scalars(stmt.order_by(Vendor.name)))


@router.post("", response_model=VendorRead, status_code=201)
def create_vendor(body: VendorWrite, session: Session = Depends(get_session)) -> Vendor:
    _one_of(body.role, ROLES, "role")
    _one_of(body.status, STATUSES, "status")
    existing = session.scalar(select(Vendor).where(func.lower(Vendor.name) == body.name.lower()))
    if existing is not None:
        # one record per vendor is the whole point — "Eaton" and "eaton" are the same firm
        raise HTTPException(status_code=409, detail=f"'{existing.name}' is already on the roster")
    v = Vendor(**body.model_dump())
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


@router.get("/{vendor_id}", response_model=VendorDetail)
def get_vendor(vendor_id: uuid.UUID, session: Session = Depends(get_session)) -> VendorDetail:
    v = _vendor(session, vendor_id)
    contacts = list(
        session.scalars(
            select(VendorContact)
            .where(VendorContact.vendor_id == v.id, VendorContact.active.is_(True))
            .order_by(VendorContact.name)
        )
    )
    quotes = list(session.scalars(select(Quote).where(Quote.vendor_id == v.id)))
    return VendorDetail(
        **VendorRead.model_validate(v).model_dump(),
        contacts=[VendorContactRead.model_validate(c) for c in contacts],
        bid_count=len(quotes),
        award_count=len([q for q in quotes if q.state == "selected"]),
    )


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: uuid.UUID, body: VendorPatch, session: Session = Depends(get_session)
) -> Vendor:
    v = _vendor(session, vendor_id)
    _one_of(body.role, ROLES, "role")
    _one_of(body.status, STATUSES, "status")
    patch = body.model_dump(exclude_unset=True)
    if patch.get("status") in ("hold", "disqualified") and not (
        patch.get("status_note") or v.status_note
    ):
        # putting a vendor out of play is a decision, and decisions carry their reason
        raise HTTPException(
            status_code=400, detail=f"marking a vendor '{patch['status']}' needs a stated reason"
        )
    for field, value in patch.items():
        setattr(v, field, value)
    session.commit()
    session.refresh(v)
    return v


@router.delete("/{vendor_id}", status_code=204)
def deactivate_vendor(vendor_id: uuid.UUID, session: Session = Depends(get_session)) -> None:
    v = _vendor(session, vendor_id)
    v.active = False  # soft — bids they gave stay attached and still feed the ROM
    session.commit()


@router.post("/{vendor_id}/contacts", response_model=VendorContactRead, status_code=201)
def add_vendor_contact(
    vendor_id: uuid.UUID, body: VendorContactWrite, session: Session = Depends(get_session)
) -> VendorContact:
    _vendor(session, vendor_id)
    c = VendorContact(vendor_id=vendor_id, **body.model_dump())
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@router.delete("/{vendor_id}/contacts/{contact_id}", status_code=204)
def delete_vendor_contact(
    vendor_id: uuid.UUID, contact_id: uuid.UUID, session: Session = Depends(get_session)
) -> None:
    c = session.get(VendorContact, contact_id)
    if c is None or c.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="contact not found")
    c.active = False
    session.commit()

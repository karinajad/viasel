import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import DemandLine, Quote
from app.schemas.sourcing import AwardRequest, QuoteCreate, QuoteRead, ScopeLineRead
from app.services.freeze import DemandNotFrozen
from app.services.sourcing import add_quote, award

router = APIRouter(tags=["sourcing"])


def _demand_line(session: Session, dl_id: uuid.UUID) -> DemandLine:
    dl = session.get(DemandLine, dl_id)
    if dl is None:
        raise HTTPException(status_code=404, detail="demand line not found")
    return dl


@router.get("/demand-lines/{dl_id}/quotes", response_model=list[QuoteRead])
def list_quotes(dl_id: uuid.UUID, session: Session = Depends(get_session)) -> list[Quote]:
    return list(
        session.scalars(
            select(Quote).where(Quote.demand_line_id == dl_id).order_by(Quote.unit_price)
        )
    )


@router.post("/demand-lines/{dl_id}/quotes", response_model=QuoteRead, status_code=201)
def create_quote(
    dl_id: uuid.UUID, body: QuoteCreate, session: Session = Depends(get_session)
) -> object:
    dl = _demand_line(session, dl_id)
    try:
        q = add_quote(
            session, dl, body.vendor, body.unit_price, oem=body.oem,
            lead_time_weeks=body.lead_time_weeks, denominator=body.denominator,
            size=body.size, terms_note=body.terms_note,
        )
    except DemandNotFrozen as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    session.commit()
    session.refresh(q)
    return q


@router.post("/demand-lines/{dl_id}/award", response_model=ScopeLineRead)
def award_quote(
    dl_id: uuid.UUID, body: AwardRequest, session: Session = Depends(get_session)
) -> object:
    dl = _demand_line(session, dl_id)
    quote = session.get(Quote, body.quote_id)
    if quote is None or quote.demand_line_id != dl_id:
        raise HTTPException(status_code=404, detail="quote not found for this demand line")
    try:
        sl = award(session, dl, quote)
    except DemandNotFrozen as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    session.commit()
    session.refresh(sl)
    return sl

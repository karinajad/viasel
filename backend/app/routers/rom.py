from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.schemas.rom import RomBand, RomPriceBatchRequest, RomPriceBatchResponse, RomPriceRequest
from app.services.rom import price, price_many, rollup

router = APIRouter(prefix="/rom", tags=["rom"], dependencies=[Depends(require_token)])


@router.post("/price", response_model=RomBand)
def rom_price(req: RomPriceRequest, session: Session = Depends(get_session)) -> RomBand:
    return price(
        session,
        req.type_query,
        req.denominator,
        req.size,
        req.qty,
        freight_unit=req.freight_unit,
        tariff_pct=req.tariff_pct,
        escalation_pct=req.escalation_pct,
    )


@router.post("/price-batch", response_model=RomPriceBatchResponse)
def rom_price_batch(
    req: RomPriceBatchRequest, session: Session = Depends(get_session)
) -> RomPriceBatchResponse:
    """ROM a whole line-item list in one call, plus the rolled-up project total."""
    bands = price_many(
        session,
        req.lines,
        freight_unit=req.freight_unit,
        tariff_pct=req.tariff_pct,
        escalation_pct=req.escalation_pct,
    )
    return RomPriceBatchResponse(lines=bands, rollup=rollup(bands))

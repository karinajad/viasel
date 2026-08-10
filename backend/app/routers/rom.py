from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.schemas.rom import RomBand, RomPriceRequest
from app.services.rom import price

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

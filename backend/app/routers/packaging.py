import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import Quote, SourcingPackage
from app.schemas.packaging import (
    CandidatesRead,
    PackageAwardRequest,
    PackageCreate,
    PackageDetail,
    PackageQuoteCreate,
    PackageRead,
)
from app.schemas.sourcing import ScopeLineRead
from app.services.freeze import DemandNotFrozen, InvalidTransition
from app.services.packaging import (
    PackagingError,
    add_package_quote,
    award_package,
    candidates,
    create_package,
    detail,
    list_packages,
    remove_line,
)

router = APIRouter(prefix="/packages", tags=["packages"], dependencies=[Depends(require_token)])


def _package(session: Session, pkg_id: uuid.UUID) -> SourcingPackage:
    pkg = session.get(SourcingPackage, pkg_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail="package not found")
    return pkg


def _conflict(e: Exception) -> HTTPException:
    return HTTPException(status_code=409, detail=str(e))


# declared before /{pkg_id} so the literal path wins the match
@router.get("/candidates", response_model=CandidatesRead)
def package_candidates(project: str, session: Session = Depends(get_session)) -> CandidatesRead:
    """The project's frozen, unpackaged demand grouped into the lots it should be bought as."""
    return candidates(session, project)


@router.get("", response_model=list[PackageRead])
def get_packages(project: str, session: Session = Depends(get_session)) -> list[PackageRead]:
    return list_packages(session, project)


@router.post("", response_model=PackageDetail, status_code=201)
def post_package(body: PackageCreate, session: Session = Depends(get_session)) -> PackageDetail:
    try:
        pkg = create_package(session, body.project_id, body.demand_line_ids)
    except (PackagingError, DemandNotFrozen) as e:
        raise _conflict(e) from e
    session.commit()
    return detail(session, pkg)


@router.get("/{pkg_id}", response_model=PackageDetail)
def get_package(pkg_id: uuid.UUID, session: Session = Depends(get_session)) -> PackageDetail:
    return detail(session, _package(session, pkg_id))


@router.post("/{pkg_id}/quotes", response_model=PackageDetail, status_code=201)
def post_package_quote(
    pkg_id: uuid.UUID, body: PackageQuoteCreate, session: Session = Depends(get_session)
) -> PackageDetail:
    pkg = _package(session, pkg_id)
    try:
        add_package_quote(
            session, pkg, body.vendor, body.unit_price,
            oem=body.oem, lead_time_weeks=body.lead_time_weeks, terms_note=body.terms_note,
        )
    except (PackagingError, DemandNotFrozen) as e:
        raise _conflict(e) from e
    session.commit()
    return detail(session, pkg)


@router.post("/{pkg_id}/award", response_model=list[ScopeLineRead])
def post_award(
    pkg_id: uuid.UUID, body: PackageAwardRequest, session: Session = Depends(get_session)
) -> object:
    pkg = _package(session, pkg_id)
    quote = session.get(Quote, body.quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="quote not found")
    try:
        scope_lines = award_package(session, pkg, quote)
    except (PackagingError, DemandNotFrozen, InvalidTransition) as e:
        raise _conflict(e) from e
    session.commit()
    for sl in scope_lines:
        session.refresh(sl)
    return scope_lines


@router.delete("/{pkg_id}/lines/{dl_id}", response_model=PackageDetail)
def delete_package_line(
    pkg_id: uuid.UUID, dl_id: uuid.UUID, session: Session = Depends(get_session)
) -> PackageDetail:
    pkg = _package(session, pkg_id)
    try:
        remove_line(session, pkg, dl_id)
    except PackagingError as e:
        raise _conflict(e) from e
    session.commit()
    return detail(session, pkg)

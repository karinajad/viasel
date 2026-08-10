# Plan: Sourcing — EXECUTED

## Goal
Turn frozen demand into committed supply: solicit competing quotes, level them, award one.

## Success Criteria
- [x] `quote` + `scope_line` tables (schema `viasel`, migration 0002)
- [x] Quotes/award only allowed against **frozen** demand (the §37 gate, enforced)
- [x] Award creates a scope line matched to the demand + advances it `frozen → matched`; qty inherited
- [x] API: list/create quotes, award; gate violations → 409
- [x] UI: demand board rows expand into a sourcing panel (add quote → level → Award)
- [x] Verified live end-to-end on Supabase; backend ruff/mypy/pytest (13) + frontend lint/build green

## What was built
- `backend/app/models.py` — `Quote`, `ScopeLine`; migration `0002_sourcing.py`.
- `backend/app/services/sourcing.py` — `add_quote` (gate), `award` (creates scope line, transitions demand).
- `backend/app/schemas/sourcing.py`, `backend/app/routers/sourcing.py` (registered in main).
- `backend/tests/test_sourcing.py` — can't-quote-unfrozen; quote→award→matched.
- `frontend/src/App.tsx` — `SourcingPanel` (quotes leveling + award) inside the demand board; `Quote` type.

## The loop now
`price → save demand → freeze → source (quotes) → award → matched (committed supply)`.
That's demand-through-award: the spine of the program, usable in the browser.

*Next faces: Agreement/Exhibits, Change events, Cost reconciliation (the wedge).*

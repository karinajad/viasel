# Plan: API Routers — EXECUTED

## Goal
Expose the engine over HTTP so the frontend (and demos) can use it.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/rom/price` | price a requirement → `RomBand` |
| GET | `/equipment-types` | taxonomy (frontend dropdown) |
| POST | `/demand-lines` | create a demand line (state `drafted`) |
| GET | `/demand-lines?project=&state=` | list |
| POST | `/freeze` | freeze lines → `FreezeEvent` (commits) |
| POST | `/thaw` | thaw lines → `ThawEvent` (commits) |
| GET | `/health` | liveness |

## Success Criteria
- [x] `POST /rom/price` returns a band from live Supabase (verified: 8 comparables, high)
- [x] `GET /equipment-types` returns the taxonomy
- [x] `POST /demand-lines` creates a drafted line
- [x] Freeze/thaw gate errors surface as HTTP 409
- [x] CORS allows the Vite dev origin
- [x] ruff + mypy + pytest green (11 passed)

## What was built
- `backend/app/routers/rom.py`, `backend/app/routers/demand.py` — routers.
- `backend/app/schemas/demand.py`, `rom.py` — request/response models (`from_attributes`).
- `backend/app/main.py` — router registration + CORS for `http://localhost:5173`.
- `backend/tests/test_api.py` — TestClient tests (read-only + a create that cleans up).

## Notes
- Services still own no commits; routers commit. Gate violations (`InvalidTransition`, `DemandNotFrozen`) → 409.
- API tests tag rows `APITEST` and delete them, so the live DB stays clean.

*Next: `plans/05-frontend-rom-calculator.md` — the live ROM Calculator screen.*

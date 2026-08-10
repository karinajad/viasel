# Plan: Hardening (functionality, not pilot-data) — EXECUTED

Focus per direction: **system functionality, not tuning the pilot data.** (ROM matching/reconciliation left as-is; data is sample fuel.) Confirmed the taxonomy contains **no location-as-type** entries (CMDA/MNR/Compute/Mech are locations, never equipment types).

## Done
- **API auth (real security fix).** `app/deps.py` `require_token` — shared `X-API-Key` on all routers (`/health` open). Closes the open-backend hole. Frontend sends the key; `test_requires_api_key` asserts 401 without it.
- **Thaw in the UI.** `services/freeze.py` `thaw_line` finds the latest freeze event covering a line; `POST /demand-lines/{id}/thaw`; a **Thaw** button on frozen/matched rows (reopens → `thawed`, history preserved).
- **Project selection.** Project is an input (no longer hardcoded `DEMO`); drives save, board, freeze.
- **Normalized leveling.** Quotes carry denominator + size; the sourcing table shows a **normalized $/denominator** column so vendors compare apples-to-apples (not just raw price).

## Deliberately NOT done (and why)
- **Quantity-tier / recency in the ROM** — need tier history + executed dates not in the data. Fabricating them is noise, not robustness.
- **Bulk import of more executed history** — data top-up, not a code piece; addable anytime.

## Config
- `backend/.env`: `API_TOKEN` (defaults `viasel-dev`); frontend `VITE_API_TOKEN` matches. Set a real one before public deploy.

Validation green: backend ruff/mypy/pytest (14) + frontend lint/build. Auth verified live (401 → 200).

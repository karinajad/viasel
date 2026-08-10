# Plan: Demand Capture + Freeze UI — EXECUTED

## Goal
Make the Design face a real loop: price a requirement → **save it as a demand line** → see it on a board → **freeze** it. No more price-and-forget.

## Success Criteria
- [x] "Save as demand line" persists the ROM result (price, confidence, spec) as a `drafted` demand line
- [x] Demand board lists a project's lines with state chips
- [x] Select drafted lines + choose scope → **Freeze** → state flips to `frozen`
- [x] Verified live end-to-end against Supabase (create → list → freeze → frozen)
- [x] backend ruff/mypy/pytest + frontend lint/build green

## What was built
- `backend/app/schemas/demand.py` — `DemandLineCreate` now captures `rom_unit_price/confidence/comparables_count`; `DemandLineRead` returns `spec_attributes`.
- `frontend/src/App.tsx` — calculator gains **Save as demand line**; new **DemandBoard** (list + checkboxes + scope + Freeze), TanStack Query invalidation so the board refreshes on save/freeze.
- `frontend/src/types/rom.ts` — `DemandLineRow`.

## The loop, live
`price (ROM) → Save → board shows it drafted → select + Freeze → frozen`.
Frozen demand is now what Sourcing (next face) will buy against.

*Next face: Sourcing — buy-by queue → quotes → leveling → award.*

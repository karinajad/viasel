# Plan: Freeze State Machine + Gate — EXECUTED

## Goal
Give demand lines a guarded lifecycle, implement freeze/thaw, and enforce the §37 gate: supply can never be committed against demand that isn't frozen.

## Success Criteria
- [x] Illegal state transitions are rejected
- [x] `freeze()` flips lines to `frozen` and records a `FreezeEvent` snapshot
- [x] `thaw()` flips lines to `thawed`, records a `ThawEvent`; refreeze works
- [x] `assert_frozen_for_supply()` refuses drafted/thawed, allows frozen
- [x] ruff + mypy + pytest green (each test rolls back — live DB untouched)

## What was built
- `backend/app/services/freeze.py` — state machine (`drafted → frozen → matching → matched → satisfied`; `frozen → thawed → frozen`; `cancelled`), `freeze`, `thaw`, `assert_frozen_for_supply`, typed exceptions.
- `backend/tests/test_freeze.py` — illegal transition, gate block→allow, thaw/refreeze history.
- `backend/app/models.py` — added Python-side defaults (`state='drafted'`, `revision=1`).

## Design notes
- Services do **not** commit — the caller owns the transaction (keeps tests rollback-clean and lets the API compose).
- Freeze/thaw store demand-line id **snapshots** (JSONB), so history = "what was frozen, when, what thawed it," not just the latest state.

*Next: `plans/03-rom-engine.md` — the seven-layer ROM band (where the reconciliation misses get closed).*

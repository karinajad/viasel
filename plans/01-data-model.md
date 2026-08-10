# Plan: Data Model (demand, freeze, price history) — EXECUTED

## Goal
Create the five Phase-1 tables in a dedicated `viasel` schema on Supabase Postgres, seed the canonical taxonomy + sample executed prices, and prove normalization reconciles to the dollar.

## Success Criteria
- [x] `alembic upgrade head` creates the `viasel` schema + five tables on Supabase
- [x] Seed loads taxonomy + executed prices (`33 equipment_type, 108 executed_scope_line`)
- [x] `ruff` + `mypy` clean
- [x] Reconciliation test: executed rows reproduce hand-built all-in within 0.1% (**25/44**)

## What was built
| File | Purpose |
|---|---|
| `backend/app/models.py` | 5 SQLAlchemy models in schema `viasel` (single source of truth) |
| `backend/database/migrations/versions/0001_initial.py` | creates schema + tables via `Base.metadata.create_all` |
| `backend/app/seed/seed.py` | loads `rom_seed/*.csv` → DB (idempotent) |
| `backend/tests/test_data.py` | `test_tables_seeded` + `test_reconciles_to_the_dollar` |

## The five tables (schema `viasel`)
`equipment_type` (physics taxonomy) · `executed_scope_line` (price corpus + confidence tier) · `demand_line` (§1, JSONB spec_attributes, state default `drafted`) · `freeze_event` · `thaw_event`.

## Validation (re-runnable)
```bash
cd backend
PYTHONPATH=. .venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python -m app.seed.seed
.venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/pytest -q -s
```

## Notes
- Runs against Supabase via the Session pooler (`DATABASE_URL` in `backend/.env`, git-ignored).
- The reconciliation misses (generators, combined transformers) are the rows whose freight/one-time/first-of-kind layers the *sample extract* dropped — captured as open work for the full ROM engine (plan 03), not a model problem.

*Next: `plans/02-freeze-state-machine.md` and `plans/03-rom-engine.md`.*

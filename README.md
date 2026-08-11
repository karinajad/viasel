# Viasel

The system of record for owner-furnished (OFCI) capital equipment across its whole life —
design → procurement → logistics → handover → operation → disposition. **One record per unit,
owned by the equipment**, not by a project, platform, or party. It outlives every system it
touches.

Not construction software. Construction is the upstream **clock** that sets need-by dates.
Schedulers (P6) and cost systems (Procore) are inputs and consumers, never the system of record.

## Repo layout
- `docs/` — product docs (concept, build spec, walkthrough, wireframes, roadmap, MVP build plan)
- `plans/` — plans of record, `00`–`12`. Executed through `11`; `12` is the current plan.
- `backend/` — FastAPI · SQLAlchemy 2.0 · Alembic · Postgres (Supabase)
- `frontend/` — Vite · React · TypeScript · TanStack Query
- `CLAUDE.md` — full project context; read it first

## What works today, live against Supabase

**Projects** — create a project, then the detail that lets history be inferred onto it: site
code, buyer entity, address, MW IT, redundancy, cooling, elevation, ambient max, sound limit.
Building/area codifiers nest by leading-code match, each building carrying its share of the MW
with a reconciliation check. Accountable and responsible by function. Freezing the legend locks
the **codes** — capacity and labels stay editable, because a building's MW is an attribute, not
its identity.

**Demand** — two workflows, deliberately apart.
- *Design register*: type · size · qty · location · required-by · long-lead weeks. **No cost.**
  Design declares what's needed; pricing it is a separate act.
- *ROM*: prices the register in place, re-runnable as the corpus grows — or prices one item
  deliberately with its **comparables grouped by supply route**. That grouping matters: the
  5000kVA transformer band looks like eight comparables at "high confidence" and is really two
  populations 1.9× apart, so the median is decided by which route has more rows. Taking anything
  other than the median requires a stated reason.

Freeze scope is the project's location legend — `project | building | area` — and it *selects*
the lines rather than labelling a hand-picked set.

**Sourcing** — frozen demand grouped into **bid packages**: lots pooled on physics (same type,
same size) across every building they land in. Bids are leveled **all-in** — equipment plus
services, freight, discount, and a one-time cost that amortises over the lot, which is why
splitting a lot costs more than the unit prices suggest. Compare per denominator, against the
lowest awardable bid, and against the ROM the record already carried. Ruled-out bids stay as
market data with their reason. Award fans one scope line out to every unit's record.

**Agreements** — the instrument that commits an awarded lot. Contract value is **derived** from
the scope lines, never stored, so the document and the record cannot hold two different totals.
Exhibits are **views of the record**: cover sheet, equipment list and legend generate; delivery
schedule, spares, bill of materials, shipping capacity and Schedule D are entered per vendor
against the units allocated to them at sourcing. Releasing hands the data over — signing happens
in whatever system the client already signs in — and the executed version comes back to be
reconciled field by field. Divergence is flagged and never applied.

**Vendors** — one record per firm, with the OEMs they actually manufacture through, factory and
integration location, sub-supplier, and a status that needs a stated reason to put a firm out of
play. Bids name a roster vendor, which is what finally makes vendor reliability computable.

**Proven:** normalized executed prices reconcile to the known all-in to the dollar. Bid leveling
reproduces their own Cheyenne chiller sheet exactly from layered inputs.

## Confidential data — not in this repo
All real OFCI source data (executed contracts, vendor pricing, supplier contacts) and extracted
price files are **git-ignored** and stay local only. See `.gitignore`. `rom_seed/` holds sample
executed prices. **The pilot data is fuel, not a feature** — logic is not tuned to it.

## Run it
```bash
# backend — needs backend/.env: DATABASE_URL (Supabase session pooler), API_TOKEN
cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000   # no --reload
PYTHONPATH=. .venv/bin/alembic upgrade head
.venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/pytest

# frontend — localhost:5173, password gate 'viasel'
cd frontend && npm run dev
npm run lint && npm run build
```

## What's next
`plans/12` — dates, allocation, and change. In order:

1. **Client milestones at project level** — the dates we receive, keyed to the location legend.
2. **The date chain** — required-by derives from the governing milestone; the vendor ROJ derives
   from required-by; the must-buy-by date derives from lead time. Every allowance a visible
   project parameter, every override recorded.
3. **Allocation-optional equipment** — you don't always know which hall a unit is going to, and
   firming that up later is a change event, not a demand revision.
4. **Change orders** — append-only scope lines, the pre-tax/tax value waterfall, approved kept
   apart from contemplated.
5. **Schedule ingest** — P6 / GC upload or port, feeding the milestone object. Last on purpose:
   settle the shape by hand before building an importer for it.

Then: cost reconciliation against the contract system — the wedge that catches the
$1.279M-class gap — followed by logistics/custody, operations, and disposition.

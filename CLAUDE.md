# Viasel — project context (read this first)

## What this is — the framing that matters
Viasel is the **system of record for owner-furnished (OFCI) capital equipment across its whole life** —
design → procurement → logistics → handover → operation → disposition. **One record per unit, owned by the
equipment**, not by a project, platform, or party. It outlives every system it touches.

- **NOT construction software.** Construction is just the upstream **clock** that sets *need-by dates*.
  Schedulers (P6) and cost systems (Procore) are **inputs and consumers, never the system of record.**
- **The problem it solves:** the physical unit has no home — it lives in the gaps *between* systems
  (Procore/P6/CxAlloy/Excel) and in people's heads, and is re-described 4–5 times, reconciled by hand.
  Chronic and **structural** (even Intel runs production schedules in Excel and stores per-item docs nowhere).
- **Generalizes** to utilities/substations, renewables/BESS, semiconductor fabs, hospitals — same buyer shape:
  an owner buying comparable capital equipment repeatedly, through multiple parties, physics-priceable.
  Data-center OFCI is the sharpest wedge. Swap the taxonomy + the clock, the record is identical.

## Core architecture principles
- **Normalize on physics, map the codes.** Price per natural denominator (`$/ton, $/kVA, $/kW, $/MW, $/MVA, $/ft, $/A`).
  Codes (budget/OFCI/building/location) are **per-project attributes via a crosswalk**, never join keys.
  An equipment-type name is **physics only**; location, vendor, phase, first-of-kind are attributes.
  (⚠️ `CMDA`/`MNR`/`Compute`/`Mech` are **locations, not equipment types.**)
- **Demand → freeze → match.** Demand originates at design; the ROM prices it from executed history.
  **Freeze** locks it (reopenable). Scope is the project's **location legend** — `project | building | area`,
  because design releases by place — and the scope *selects* the lines rather than labelling a hand-picked set
  (`freeze_event.scope_ref` records which). Grouping equipment to price to one vendor is a **sourcing** concern
  (bid packages), never a freeze scope; `system` was dropped from spec §3 for that reason. **Only frozen demand
  is sourceable — the gate.**
  Award commits supply and matches it. Every change is a disturbance to the match.
- **Custody follows title.** Record owned by whoever holds title; transfers down the ownership chain
  (each holder becomes a subscriber); provenance gifts at handover, cross-campus pricing stays with the developer.
- **Everything is a byproduct of one well-kept record** — ROM, turnover, monitoring, residual value all fall out.
  Front-loaded judgment: depth once at setup; everything downstream is administration.
- **Structure enforces itself / audit trail.** Legend codifiers freeze (thaw needs a *stated reason*, logged);
  codes persist **forever** (soft-delete + crosswalk).

## What's built (LIVE against Supabase)
- **Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · Postgres (Supabase, **session pooler**). Vite · React · TS · TanStack Query.
  API-key auth (`X-API-Key`). Checks: `ruff` `mypy` `pytest` (backend), `oxlint` `tsc -b` `vite build` (frontend).
- **DB schema `viasel`:** `equipment_type`, `executed_scope_line` (price corpus), `demand_line`, `freeze_event`,
  `thaw_event`, `sourcing_package`, `package_line`, `quote`, `scope_line`, `project`, `project_location`,
  `legend_event`, `project_contact`, `vendor`, `vendor_contact`. Migrations `0001`–`0012`. Two rules live in the DB, not just in code: a demand line can be
  in only one open package (partial unique index), and a quote targets a package **xor** a demand line (CHECK).
- **Frontend = wireframe shell** (road pipeline + role tabs). Live faces:
  - **Projects** — create project · **project detail for inference** (site code · buyer entity · address ·
    MW IT · redundancy · cooling · elevation · ambient max · sound limit — typed, because inference queries
    them) · nested building/area codifiers with **per-building MW** and a capacity reconciliation check ·
    **accountable & responsible by function** (recorded, not enforced — no user model) · **freeze legend**.
    No energization date: that's a schedule output and P6 owns it; the record carries per-unit required-by.
  - **Vendors** — one record per firm (dedup by name), role (oem/distributor/integrator/supplier), the OEMs
    they actually manufacture through, factory/integration location, sub-supplier, status with a **required
    reason** for hold/disqualified, contacts. Bids name a roster vendor (`quote.vendor_id`), and a vendor on
    hold can't be bid — which is what finally lets §11 vendor reliability accumulate.
  - **Demand** — two workflows, deliberately apart. **Design register**: `Type ▾ · Size ▾ · Qty ·
    Location ▾ · Required by · LLE`, **no cost** — design declares what's needed, where, by when.
    **ROM**: prices the register in place (`POST /demand-lines/price`, re-runnable, drafted only), or
    prices one item deliberately with its **comparables grouped by supply route** and a selectable basis
    (median/low/high/route) that **requires a stated reason** when it isn't the median. Freeze scope is
    `project | building | area` and *selects* the lines.
  - **Sourcing** — per project: frozen demand grouped into **bid packages** (lots pooled on physics —
    same type + size, across buildings) → one bid per vendor for the whole lot → **leveling** (per
    denominator, vs lowest, vs the ROM the record carried) → award, which fans **one scope line out to
    every unit's record** at its own qty. Gate-enforced at form, bid, and award; award is two-step.
  - Cost · Logistics · Vendor · Operations · Disposition · Program — **polished previews, NOT built.**
- **Proven:** normalized executed prices reconcile to the known all-in **to the dollar** (25/44 sample rows within 0.1%).

## Key endpoints (all require `X-API-Key`)
`GET/POST /projects` · `GET/POST/PATCH/DELETE /projects/{id}/locations` · `POST /projects/{id}/legend/freeze|thaw`
· `GET /equipment-types` · `POST /rom/price` · `POST /rom/price-batch` (whole list + rollup)
· `GET/POST /demand-lines` · `POST /demand-lines/batch` · `POST /demand-lines/price` · `GET /freeze/preview` · `POST /freeze`
· `POST /demand-lines/{id}/thaw`
· `GET /packages/candidates?project=` · `GET/POST /packages` · `GET /packages/{id}` · `POST /packages/{id}/quotes`
· `POST /packages/{id}/award` · `POST /packages/{id}/lines` (move/combine) · `POST /packages/{id}/split`
· `POST /packages/{id}/merge-lines` · `POST /packages/{id}/quotes/{q}/decline` · `DELETE /packages/{id}/quotes/{q}`
· `DELETE /packages/{id}/lines/{dl_id}`
· `GET/POST /demand-lines/{id}/quotes` · `POST /demand-lines/{id}/award` (the package-of-one shortcut; the UI
uses packages) · `GET /health` (open).

## Roadmap — next up (NOT built)
**`plans/12` is the current plan — dates, allocation, and change.** It came out of asking where ROJ
dates come from, which exposed three problems behind one typed field:

1. **Client milestones at project level.** There are two ROJs: what the client tells us must be
   complete (the parameter the ROM plans against) and what we put on a PO (deliberately months
   earlier). Milestones are keyed to the **location legend**, with source and provenance. We are not
   their origin — P6 owns them; manual entry is the bootstrap.
2. **The date chain — four dates, three derived.** client milestone → required-by (− site allowance)
   → vendor ROJ (− delivery buffer) → required-PO-date (− lead time, spec §6). Every allowance is a
   **visible project parameter**; every override is recorded with a reason, like `rom_basis`. The
   delivery schedule's typed ROJ date today is a **stopgap**. A milestone that moves under committed
   supply is the alert this whole chain exists to produce — never auto-applied.
3. **Allocation may be unknown at buy time.** Their Shipping Capacity tab literally has a
   *"Project Overall (if not yet itemized)"* row. Exhibits must print "not yet itemized", never a
   blank cell. Firming allocation later is a **change event with no commercial effect** (spec §19,
   origin `Program`) — *not* a demand revision, so it must not need a thaw. Unallocated demand
   freezes at project scope only.
4. **Change orders.** Append-only scope lines (`ScopeLine.change_type` exists, nothing writes
   non-baseline yet), the pre-tax/tax value waterfall, and `approved` kept apart from
   `contemplated/TBD`. Don't trust a CO's stated schedule impact — their COs report zero-day
   impact while adding whole units.
5. **Schedule ingest last** — P6/GC upload or port feeding the milestone object. Deliberately last:
   settle the shape by hand before building an importer for it.

**Also unbuilt, decided but not started:** exhibits currently need an **awarded** lot; they should be
workable against a **recommended** one (an award memo *is* the exhibits put to approvers), which means
recommending creates provisional scope lines and moves demand to `matching`. Needs a go-ahead.

**Later:** paste-from-Excel into the Design register · split award (one lot, two vendors) ·
**cost reconciliation — the wedge**, derived commitment vs. the cost/contract system, catching the
$1.279M-class gap · logistics/custody · operations telemetry · disposition/provenance.

⚠️ **Not** quantity inference from a units-per-MW ratio library. Equipment count is
`load ÷ unit size × redundancy` — an equation, not a regression, and a ratio would silently import
the last project's topology. History's role there is a check, not the source.

## How to run
```bash
# backend — needs backend/.env: DATABASE_URL (Supabase session pooler), API_TOKEN
cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000   # NO --reload (hangs on Supabase conns)
PYTHONPATH=. .venv/bin/alembic upgrade head          # migrations
.venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/pytest
# frontend — localhost:5173, password gate 'viasel', sends X-API-Key = VITE_API_TOKEN (default 'viasel-dev')
cd frontend && npm run dev
npm run lint && npm run build
```

## Conventions / gotchas
- **Confidential OFCI source data is git-ignored** (`ofci data/`, etc.). `rom_seed/` has **sample** executed prices.
- **Pilot data is a sample — do NOT tune logic to it.** Data is fuel, not a feature.
- Services don't commit; **routers commit.** Gate violations → HTTP 409.
- Python 3.14 locally (wheels fine); mypy targets 3.12.
- Frontend shared helpers live in `frontend/src/lib/` (`equipment.ts` `resolveSpec` · `locations.ts`
  `nest`/`locationOptions` · `format.ts`) — one definition per rule, used by every face.
- Deep docs: `docs/` (Concept, Build Specifications, Product Walkthrough, Wireframes, MVP Roadmap, MVP Build Plan, Spec Addendum).
  Executed plans-of-record: `plans/00`–`10`. **`plans/11` is NOT executed** — it maps the real OFCI
  documents against the Build Spec and finds that **spec PART II (§5–§11) already specifies most of
  sourcing** (lead-time trust layers, solicitation, delivery cadence, 6-dimension leveling, three
  readiness tracks, vendor performance) and §13/§15 specify cancellation/LD/payment terms. The gap is
  implementation, not specification. Read `plans/11` before extending sourcing.

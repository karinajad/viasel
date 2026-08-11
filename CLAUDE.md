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
  `legend_event`. Migrations `0001`–`0007`. Two rules live in the DB, not just in code: a demand line can be
  in only one open package (partial unique index), and a quote targets a package **xor** a demand line (CHECK).
- **Frontend = wireframe shell** (road pipeline + role tabs). Live faces:
  - **Projects** — create project · nested building/area codifiers (edit/delete/sort) · **freeze legend** (thaw needs reason).
  - **Demand Management (Design & ROM)** — a duo: **Line-item list** (stack `Type ▾ · Size ▾ · Qty ·
    Location ▾` rows → one button ROMs the whole list into a WIP project ROM → saves all as drafted demand)
    and **Quick price** (one requirement, full layer breakdown). Denominator + size derive from the
    equipment; locations come from the project's codes. Then freeze/thaw on the shared demand board.
  - **Sourcing** — per project: frozen demand grouped into **bid packages** (lots pooled on physics —
    same type + size, across buildings) → one bid per vendor for the whole lot → **leveling** (per
    denominator, vs lowest, vs the ROM the record carried) → award, which fans **one scope line out to
    every unit's record** at its own qty. Gate-enforced at form, bid, and award; award is two-step.
  - Cost · Logistics · Vendor · Operations · Disposition · Program — **polished previews, NOT built.**
- **Proven:** normalized executed prices reconcile to the known all-in **to the dollar** (25/44 sample rows within 0.1%).

## Key endpoints (all require `X-API-Key`)
`GET/POST /projects` · `GET/POST/PATCH/DELETE /projects/{id}/locations` · `POST /projects/{id}/legend/freeze|thaw`
· `GET /equipment-types` · `POST /rom/price` · `POST /rom/price-batch` (whole list + rollup)
· `GET/POST /demand-lines` · `POST /demand-lines/batch` · `GET /freeze/preview` · `POST /freeze`
· `POST /demand-lines/{id}/thaw`
· `GET /packages/candidates?project=` · `GET/POST /packages` · `GET /packages/{id}` · `POST /packages/{id}/quotes`
· `POST /packages/{id}/award` · `POST /packages/{id}/lines` (move/combine) · `POST /packages/{id}/split`
· `POST /packages/{id}/merge-lines` · `POST /packages/{id}/quotes/{q}/decline` · `DELETE /packages/{id}/quotes/{q}`
· `DELETE /packages/{id}/lines/{dl_id}`
· `GET/POST /demand-lines/{id}/quotes` · `POST /demand-lines/{id}/award` (the package-of-one shortcut; the UI
uses packages) · `GET /health` (open).

## Roadmap — next faces (NOT built)
- **Paste-from-Excel into the line-item grid:** the real unlock for hundreds of lines — needs its own
  column-mapping face.
- **Split award** (one lot, two vendors by building) — schema already allows it, allocation rules don't exist yet.
  Same for cancelling a package and vendors as records rather than typed strings.
- **Agreement / Exhibits:** exhibits are **generated from the record** (never a template a counterparty fills in),
  through a **contracts portal**; the **executed (signed) exhibit is stored back and reconciled field-by-field**
  against what Viasel generated (flag any drift); **required-document dropdowns keyed to lifecycle gates** (Schedule D),
  with *"prior to final payment"* as a withholding/retainage lever.
- **Cost reconciliation (the wedge):** record's derived commitment vs. the cost/contract system → catches the
  $1.279M-type gap. Logistics/custody · Operations (telemetry) · Disposition/provenance.

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

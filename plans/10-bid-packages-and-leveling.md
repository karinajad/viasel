# Plan: Sourcing — bid packages, scoped per equipment, and bid leveling — EXECUTED

## Goal
Sourcing draws the **project** in, scopes the buy **per equipment**, and levels the bids against it.

The old face sourced one demand line at a time. That's not how anyone buys: you don't RFQ the twelve
transformers in hall C1-DH3 and then RFQ the eight in C2 — you RFQ every 5000kVA transformer on the
project as one lot, and you ask each vendor for one number. A per-line face made the buyer enter the
same vendor three times and level three times, and nothing in the record ever said what the
*project's* buy of that equipment was.

## The concept
- A **bid package** is the lot: frozen demand lines pooled on **physics** — same type, same
  denominator, same size — across every building they land in.
- **Pooling is strict** (type + size). Mixing sizes in one lot would let a single vendor number stand
  in for two different physical things.
- One **bid per vendor for the whole lot**, priced per unit.
- **Leveling** puts them on the same footing: normalized per the natural denominator, extended over
  the lot, delta vs. the lowest bid, and delta vs. **the ROM the record already carried** — so the
  question isn't just "who's cheapest" but "has the market moved off our executed history".
- **Award** commits the lot to one vendor and **fans a scope line out to every unit's own record**,
  each matched to its own demand line at its own quantity. The package is the vehicle; the unit
  record is still the thing.

## Success criteria
- [x] Sourcing is project-scoped: candidate lots and packages both keyed to the project
- [x] Candidate lots computed from the project's frozen, **unpackaged** demand, grouped by physics
- [x] Strict pooling enforced (mixed sizes → 409)
- [x] Bids at package level, leveled per denominator, vs. lowest and vs. ROM
- [x] Award fans out one scope line per demand line, each at its own qty; every line → `matched`
- [x] The §37 gate holds at every step: form, bid, award
- [x] Migration `0005` applied to Supabase · 32 backend tests · frontend lint / tsc / build green

## What was built

### Schema — migration `0005`
- `sourcing_package` — project_id, `code` (PKG-01… per project), equipment_type_id, type_query,
  denominator, size, `state` (open | awarded | cancelled).
- `package_line` — package ↔ demand line, **soft-deleted** (`active`), so re-packaging keeps its
  history the way `project_location` keeps retired codes.
- **Structure enforces itself, in the DB:**
  - partial unique index `package_line_one_active on (demand_line_id) where active` — a unit cannot
    sit in two open packages, so it cannot be double-sourced;
  - `quote.demand_line_id` relaxed to nullable, `quote.sourcing_package_id` added, with
    `CHECK ((demand_line_id IS NULL) <> (sourcing_package_id IS NULL))` — a bid targets a package or
    a single line, never both, never neither.

### Backend — `app/services/packaging.py`
`pool_key` (physics identity from `spec_attributes`) · `candidates` · `create_package` ·
`remove_line` · `add_package_quote` · `award_package` · `leveling` · `detail` · `list_packages`.
Endpoints: `GET /packages/candidates?project=` · `GET/POST /packages` · `GET /packages/{id}` ·
`POST /packages/{id}/quotes` · `POST /packages/{id}/award` · `DELETE /packages/{id}/lines/{dl_id}`.
Every rule violation is a 409, never a silent skip.

### Frontend — `src/Sourcing.tsx`
- **① Scope the buy** — candidate lots, biggest first: equipment, which buildings, lines, units, ROM
  extended, and *Scope as package ▸*.
- **② Bid packages** — code, equipment, units, ROM extended, bid count, state, awarded vendor and
  amount. Expand for the lot contents (drop a line while open — it returns to the candidate pool) and
  the leveling table.
- **Award is two-step**: *Award ▸* → *Commit $6,121,480*, with the consequence spelled out first.
  It commits supply for every unit in the lot; that shouldn't be one click.
- `src/types/sourcing.ts`; `signed`/`signedPct`/`physics` added to `lib/format.ts`.

## Design decisions
- **A package is a vehicle, not a record.** Award writes scope lines against demand lines, exactly as
  the per-line path did. Nothing about ownership of the unit moves into the package.
- **Leveling computed server-side**, next to the ROM it compares against — one definition, and the
  frontend renders rather than recomputes.
- **The per-line quote/award endpoints stay** (they're the package-of-one shortcut, and tests cover
  them), but the Sourcing face is packages only. A single frozen line is scoped as a lot of one, so
  there's one motion in the UI instead of two.
- **Lines with no physics captured are excluded and counted**, not pooled into a junk lot. A line with
  no equipment type has nothing to bid against, and the face says so.

## Verified live (Supabase)
Three frozen lines (5000kVA ×12 in C1-DH3, ×8 in C2; 3250kVA ×4 in C3) →
- candidates: **20-unit 5000kVA lot** (C1 C2, ROM $6,399,240) and a separate 4-unit 3250kVA lot;
- mixing the two → **409, one equipment type at one size**;
- three bids leveled: Parrish Hare **$61.21/kVA** ($6,121,480, −$13,888/unit vs ROM) · Powell
  $68.24 (+$35,126 vs low) · Eaton $101.51 (+$201,459 vs low);
- award → 2 scope lines (×12 and ×8) at $306,074, both lines `matched`, package `awarded`,
  −$277,760 against the ROM the record carried;
- after award: second award 409 · late bid 409 · re-packaging an awarded line 409;
- the 3250kVA lot still sits in candidates, unbought. Test data removed.

## Not done (deliberately)
- **Split award** (one lot, two vendors by building). The schema already allows it — each demand line
  gets its own scope line with its own vendor — but the UI and the allocation rules are their own face.
- **Cancel a package.** `cancelled` exists in the state vocabulary; nothing sets it yet.
- **Vendor as an entity.** Vendors are still free-typed strings; a vendor record belongs with the
  vendor portal.

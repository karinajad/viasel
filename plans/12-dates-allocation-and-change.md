# Plan: Dates, allocation, and change — NOT EXECUTED

## What ROJ exposed
Asking "where do ROJ dates come from" turned up three separate problems hiding behind one
typed field.

1. **There isn't one ROJ, there are two.** The client tells us when things must be complete —
   that's the date the ROM plans against. The date we put on a purchase order is deliberately
   *earlier*, because we want equipment on site months before the site needs it. Today the
   delivery schedule takes one typed date and calls it ROJ, which conflates a parameter we
   receive with a commitment we set.
2. **Allocation isn't always known when you buy.** Sometimes you don't yet know which hall a
   unit is going to, and it changes later. The record currently assumes every demand line has
   a building.
3. **Both of those keep moving after execution**, and there is nowhere for that to land.

---

## A. The date chain — four dates, three of them derived

| # | Date | Lives on | Comes from |
|---|---|---|---|
| 1 | **Client milestone** | project (new) | the client / GC schedule — a parameter we receive |
| 2 | **Required-by, per unit** | `demand_line.required_by_date` (exists, typed) | milestone − site allowance (install + commissioning) |
| 3 | **Vendor ROJ** | delivery-schedule row (`exhibit_item.due_date`, exists, typed) | required-by − delivery buffer ("a couple of months") |
| 4 | **Required-PO date** | derived, not stored — spec §6 | required-by − lead time − buffer |

Only #1 is entered. Everything else is arithmetic on it, and each allowance is a **visible
parameter on the project**, not a constant buried in code — the same argument that put
escalation on the project rather than in a form.

**Derived by default, overridable with the override recorded.** Reality intrudes and a date
will sometimes be set by hand; what must not happen is a hand-typed date that looks derived.
Same shape as `rom_basis` / `rom_note`: take the default silently, depart from it with a reason.

Note #4 is not a delivery date at all — it's the date *we* have to be in contract by, and its
absence is why "we're late to buy" stays invisible until it already is.

## B. Client milestones at project level

New object, sitting beside the project's codifiers and its capacity:

```
PROJECT_MILESTONE
  project_id · name                  → "C1 energization", "DH3 ready for equipment"
  scope · scope_ref                  → the location legend again: project | building | area
  milestone_date · source            → client | GC | internal
  confirmed_at · confirmed_by        → provenance, because these move
  supersedes_id                      → the previous version of this milestone
```

Keyed to the **location legend**, so a milestone governs a building or a hall and the demand
lines in it inherit from it. Same axis as freeze scope, for the same reason: schedule releases
by place.

Two rules that matter more than the object:

- **We are not the source.** P6 and the client's commissioning schedule own these dates; Viasel
  holds the version it was told, with provenance. Manual entry is the bootstrap, not the design.
- **A milestone that moves under committed supply is the alert.** When a re-issued schedule
  pulls a date in on a unit already in production, that's a disturbance to the match and the
  single most valuable thing this whole chain produces. Never auto-apply it silently.

## C. Allocation may be unknown, and their own sheet says so

The Shipping Capacity tab has a literal row: **"Project Overall (if not yet itemized)"**. That
is the affordance for exactly this, already in their workbook, and I built past it.

- `demand_line.target_building` is already nullable, and candidate lots already group
  unallocated lines under "unassigned". The model tolerates it; the faces don't say so.
- Exhibits must print **"not yet itemized"** rather than a blank cell. A blank reads as an
  omission; "not yet itemized" is a claim, and the difference shows up in a signed document.
- **Firming allocation later is not a demand revision.** The quantity and the spec haven't
  changed, only where the unit lands. Spec §19 already classifies this: origin `Program`,
  resolution *rematch*, **no commercial effect**. So it must not require a thaw.
- Consequence for freeze scope: unallocated demand freezes at **project** scope. Building and
  area scope only cover what's been allocated. That's consistent rather than a special case —
  the scope axis is the location legend, and an unallocated line isn't in a location yet.

## D. Change orders — where all of this moves after execution

Their CO Equipment List tab is already the specification: `Change Type` ·
`Description of Change` (separate from the item description) · `Tax / Tariff / Logistics Change`
per line. And `ScopeLine.change_type` already exists — `baseline | addition | deduction |
substitution | resize` — with nothing yet writing a non-baseline row.

A change order amends an executed agreement by **appending** scope lines, never editing them:

- quantity moves (add/deduct), spec changes (substitution/resize), allocation firms up, dates shift
- value is a waterfall — original → prior approved changes → current change → revised — split
  pre-tax and tax, which every executed CO in their folders shows explicitly
- the "zero-day schedule adjustment" trap: their COs report zero schedule impact even when a
  change adds or removes whole units. That field cannot be trusted at face value and has to be
  checked against the quantity and delivery data on the same document
- `approved` and `contemplated/TBD` must be separate states. A running total that blends them
  is how a $711k "TBD" roll-forward ends up looking committed

## Sequence

**A — client milestones on the project.** Small, and it unblocks the rest. Milestones keyed to
the location legend, with source and provenance.

**B — the date chain.** Site allowance and delivery buffer as project parameters; required-by
derives from the governing milestone; vendor ROJ derives from required-by; overrides recorded
with a reason. This is also where `required_po_date` and the buy-window queue land (the old
Packet 2), because they're the same arithmetic.

**C — allocation-optional.** "Not yet itemized" through the register, the lots, and the
exhibits. Allocation change as a change event with no commercial effect, no thaw required.

**D — change orders.** The CO space: append-only scope lines, the value waterfall, approved vs
contemplated kept apart, and schedule impact checked rather than believed.

**E — schedule ingest last.** P6 / GC upload or port, feeding the milestone object built in A.
Deliberately last: settle the shape with manual entry first, or you build an importer for a
model that then changes underneath it.

## Explicitly not doing

- **Viasel as the origin of client dates.** Manual entry is a bootstrap; the schedule owns them.
- **Auto-applying a re-issued schedule.** Flag the disturbance; never move a date silently
  under supply that's already committed.
- **Treating allocation as a demand revision.** It isn't one, and requiring a thaw would make
  people route around the freeze.
- **Trusting a CO's stated schedule impact.** Check it against the quantities on the same
  document.

## Corrections this plan carries forward

- The delivery schedule's typed ROJ date is a **stopgap**. It exists because there was nowhere
  else to put a date; once A and B land it should derive, and typing it becomes an override.
- Exhibits currently require an **awarded** lot. They should be workable against a
  **recommended** one — an award memo *is* the exhibits put in front of approvers — which means
  recommending creates provisional scope lines and moves demand to `matching`, with award
  flipping them to baseline. Still unbuilt and still needs a decision.

# Plan: Line-item ROM grid (the workhorse) — EXECUTED

## Goal
Stack the whole scope as rows — `Type ▾ · Size ▾ · Qty · Location ▾` — and **one button ROMs the
entire list** into a work-in-progress project ROM, then saves it as drafted demand in one shot.
Duo interface with the single-item **Quick price** calculator: same engine, same history.

The single-item calculator was the proof; the grid is how the work actually gets done. A project has
hundreds of lines, and pricing them one at a time is the reason ROMs live in Excel today.

## Success criteria
- [x] Grid rows with type / size / qty / location from **the project's own codes** (no free-typed codes)
- [x] One call prices every row and returns the rolled-up project total
- [x] One call saves the whole list as drafted demand — it then flows into the existing freeze gate
- [x] Unpriced rows are counted, never silently absorbed into the total
- [x] Editing a row voids its own price *and* the total until re-priced — nothing stale is shown as current
- [x] backend ruff/mypy/pytest (20) · frontend oxlint / tsc / vite build green

## What was built

### Backend
- `services/rom.py` split into `_comparables()` (the one DB query) and `_band()` (pure banding), so
  `price()` is unchanged and **`price_many()` reuses one corpus query per distinct
  (type, denominator)** — a 40-row grid is a handful of queries, not 40 round-trips to the pooler.
- `rollup()` — totals the bands into the WIP project ROM. Two honesty rules baked in:
  - unpriced lines (no comparables) contribute **nothing** to the totals and are reported as
    `unpriced_count`;
  - the rollup's confidence is the **weakest tier present** — a total is only as good as its worst line.
- `POST /rom/price-batch` → `{lines: [RomBand], rollup: RomRollup}`, bands in request order.
  Tariff / escalation are project-level and apply to every line; freight is per-unit so a line may
  override it. Capped at 500 lines.
- `POST /demand-lines/batch` → all of the list or none of it, every row `drafted`. Capped at 500.
- Tests: batch agrees line-for-line with the single-line engine; rollup counts the unpriced row and
  reports tier `none`; escalation scales every line; per-line freight stays on its own line;
  `rollup([])` is honest; both endpoints tested via `TestClient` (empty list → 422) with cleanup.

### Frontend
- `src/RomGrid.tsx` — the grid. Add / duplicate / remove rows; duplicate is the common motion
  (same unit, different hall). Rollup panel shows low – mid – high, line and unit counts, the weakest
  confidence, and the unpriced-lines note; then **Save all N lines as demand ▸**.
- `src/lib/` extracted so the grid and the calculator share one definition instead of two:
  - `equipment.ts` — `resolveSpec()`: pick a type and its size, and **denominator + size fall out of
    the record**. Physics only, nothing hand-entered.
  - `locations.ts` — `nest()` (areas under the building whose code is the leading match, longest
    wins — lifted out of `LocationEditor`) and `locationOptions()`, one flat list where picking an
    area carries its building along, so a demand line always lands in both.
  - `format.ts` — `money` / `TIER` / `STATE` / `describe`.
- `DemandFace` is now a segmented duo — **Line-item list** (default) | **Quick price** — over the
  shared demand board, which gained a board-total footer.
- **Quick price's building/area free-text inputs became the same Location dropdown.** Free-typing a
  code is exactly the drift the legend freeze exists to prevent; the codifiers made this fixable.

## Design decisions
- **No new table.** The work-in-progress project ROM *is* drafted demand lines — that's what
  `drafted → frozen` already means. A `rom_worksheet` table would be a second home for demand and
  cut against one record per unit.
- **One definition of the total, on the server.** Editing a row marks the rollup stale and dims it
  with *"list changed — price it again"* rather than recomputing the total in TypeScript. Two
  implementations of the project ROM would drift; a dimmed number that says so cannot lie.
- **Escalation / tariff exposed as batch inputs.** A project total that can't be escalated to the
  need-by date isn't usable as a project total. The request already carried the fields.
- **Saving an unpriced row is allowed** (with the count shown). The requirement is real whether or
  not history can price it — blocking the save would lose demand to protect a number.

## Verified live (Supabase)
- 3-row grid (5000kVA transformer ×12 · 2000kW UPS ×8 · 211kW CRAH ×24) at 5% escalation →
  **$16.5M – $17.8M – $24.6M**, 44 units, weakest tier `low`, 0 unpriced.
- Batch-saved 2 lines → `drafted`, locations landed in both building and area → froze both via the
  existing `POST /freeze` → `frozen`, i.e. sourceable. Test rows removed.

## Not done (deliberately)
- **Per-row need-by date.** The row shape is the spec'd one; dates belong with the P6 clock, not typed here.
- **Paste-from-Excel import.** The real unlock for hundreds of lines, but it needs a column-mapping
  face of its own — a plan, not a corner of this one.

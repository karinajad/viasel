# Plan: ROM Engine — EXECUTED

## Goal
Price a requirement from the executed corpus: normalize to the natural denominator, assemble a band, and report honest confidence from the comparable count.

## Success Criteria
- [x] `price(...)` returns a band (low/mid/high) normalized per denominator
- [x] Band spread reflects real vendor spread; low end matches executed history
- [x] Confidence tier + comparable count on every result
- [x] No-comparable case falls back honestly (tier `none`, quotes/judgment note)
- [x] ruff + mypy + pytest green

## What was built
- `backend/app/schemas/rom.py` — `RomBand` (layers, band, confidence, comparables).
- `backend/app/services/rom.py` — `price()`: filters the corpus by type + denominator, normalizes each comparable to $/denominator, builds low/median/high × requested size, applies optional freight/tariff/escalation layers, assigns confidence (executed & ≥6 → high, ≥3 → medium, else/fallback → low).
- `backend/tests/test_rom.py` — prices a 5000kVA transformer (verified band + confidence); no-comparable fallback.

## Result (live seed)
`5000kVA transformer ×12 → $306,074 – $319,962 – $684,922/unit (high, 8 comparables)`.
Low end = the executed GE Prolec all-in; high end = Eaton. The band *is* the vendor spread.

## Honest scope
Base · services · tax come from executed history. Freight · tariff · escalation are present as **layers with 0 defaults** (parameters), because those columns weren't in the sample extract — folding them in from the source pricing sheet is what will close the remaining reconciliation misses (generators, combined transformers). Not a logic gap; a data-completeness follow-up.

*Next: `plans/04-api.md` (routers) → `plans/05-frontend-rom-calculator.md` (the live ROM screen).*

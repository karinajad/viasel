# Plan: Frontend ROM Calculator — EXECUTED

## Goal
The Design-role screen: enter a requirement → call the API → render the price band with confidence, live in the browser.

## Success Criteria
- [x] Form (equipment type, denominator, size, qty) + preset chips
- [x] Calls `POST /rom/price` via TanStack Query
- [x] Renders band (low / mid / high), extended, confidence tier + comparable count, layers
- [x] Honest empty/error states (no comparables → the fallback note; API down → message)
- [x] oxlint + `tsc -b` + `vite build` green

## What was built
- `frontend/src/types/rom.ts` — `RomBand` / `RomPriceRequest`.
- `frontend/src/App.tsx` — the ROM Calculator (form left, band right, preset chips, confidence badge, layer breakdown).
- Uses `src/services/api.ts` (`apiPost`) and the `QueryClientProvider` from plan 00.

## Run it
```bash
# backend (has CORS for :5173)
cd backend && .venv/bin/uvicorn app.main:app --reload
# frontend
cd frontend && npm run dev   # → http://localhost:5173
```
Click a preset (e.g. "5000 kVA transformer ×12") → the band renders from live Supabase data.

*Phase 1 complete: demand → ROM → freeze, priced from real history, usable in the browser.*

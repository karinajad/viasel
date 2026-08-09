# Viasel

Equipment lifecycle "record of truth" for owner-furnished (OFCI) capital equipment
in data-center programs. One record per unit, owned by the equipment — carried from
design → procurement → logistics → handover → operation → disposition.

## Repo layout
- `docs/` — product docs (concept, build spec, walkthrough, wireframes, roadmap, MVP build plan)
- `plans/` — implementation plans (Prime → Plan → Execute → Verify workflow)
- `backend/`, `frontend/` — the application (scaffolded in plan 00)

## Confidential data — not in this repo
All real OFCI source data (executed contracts, vendor pricing, supplier contacts) and
extracted price files are **git-ignored** and stay local only. See `.gitignore`.

## MVP (Phase 1)
The ROM & Demand-Freeze engine: capture demand at design → price it from executed
history (normalized to natural denominators) → freeze it. Proof: reconcile a known
executed price to the dollar.

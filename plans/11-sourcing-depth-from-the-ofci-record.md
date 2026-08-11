# Plan: Sourcing depth, mapped from the OFCI record — NOT EXECUTED

## Goal
Reconcile what the real OFCI documents do during sourcing against (a) what the Build Specification
already says and (b) what plans `00`–`10` actually built — then sequence the gap.

**The headline finding: the specification is not the gap.** `docs/Viasel_Build_Specifications 260804.docx`
PART II (§5–§11) already specifies lead-time trust layers, solicitation, quotes with delivery capacity,
six-dimension leveling, three readiness tracks, award with declined quotes, and vendor performance
feedback. §13 already specifies cancellation tiers, liquidated damages, and payment shapes as a typed
term registry. Plans `00`–`10` built a thin slice of that: quotes, price-only leveling, single-winner award.

So this plan is mostly **"build what's already specified,"** plus a short list of things the documents
carry that the spec genuinely does not, plus two corrections to what shipped.

## What the review covered
| Read | File |
|---|---|
| Bid leveling, 19 sheets | `ofci data whole/Related Digital - Cheyenne - Bid Leveling 7.16.2025.xlsx` |
| Award recommendation form | `E2 Award Summary Sheet_Related Digital Copy.xlsx` |
| PO/CO exhibit schema | `Exhibits.xlsx` |
| Executed award memo | `ofci data whole/Mitten_OFCI Award Memo2_Vertiv_2025.12.22 - Executed.pdf` |
| Prepurchase strategy | `ofci data whole/LLE Prepurchase Strategy.pptx` |
| Stage gates + folder governance | `OFCI Program Decks/OFCI_Project Governance.pptx` |
| Budget/ACR structure | `Mitten Trackers/Mitten OFCI BBS 2026-07-17.xlsx` (BBS · Building ACR · OFCI ACR) |
| Approval workflow log | `ofci data whole/Spade Campus_COAP Log 07172026.xlsx` |
| Prior synthesis of all 148 files | `OFCI_Document_Review_Consolidated_Findings.docx` |

**Not read:** the PO/CO trackers and their four dated snapshots, submittal logs, Delivery Turnovers with
Power Ramp, the Accenture SOWs, `Standard BOD Sourcing Process.eml`, remaining executed PO PDFs,
`Program LLE Release.xlsx` / `Cartoon Schedule - LLE Prepurchase.xlsx` (the deposit tables).
Workbooks were parsed for cached cell values, not evaluated formulas.

---

## A. Already specified · not built — this is the bulk of the work

| Finding in the documents | Spec home | Built? |
|---|---|---|
| Delivery is a **cadence**: "20 March, 20 April, 20 May, 24 June"; POs commit monthly rates (PH-002: 6/month Oct 26–Sep 27) | §7 `QUOTE.delivery_capacity[]` units per period; §8 Capacity dimension | ✗ single `lead_time_weeks` int |
| Two dates, not one: **Need-by (First Gear) / (Last Gear)** vs **Supplier Commit Date** for each | §5 four date sources w/ trust; §6 `required_po_date` | ✗ |
| Lead time claimed vs achievable ruled out 3 of 6 chiller bids ("46 weeks… cannot meet Related's schedule") | §5 p50/p90 + §8 stated-vs-historical gap; §11 `VENDOR_PERFORMANCE` | ✗ |
| **Cancellation ladder** keyed to milestones: 10% PO→submittal release · 40% at production release · 75% at 90d · 100% at 60d | §13 `TERM_TYPE` cancellation schedule (tiers, triggers, basis) | ✗ |
| **Payment milestones**: 10% order · 10% submittal approval · 75% shipment · 5% retention after commissioning or 120d · Net 45 | §13 payment terms → §15 `PAYMENT_SCHEDULE` (3 shapes, `reconciles_to_100` enforced) | ✗ |
| **Liquidated damages as formulas**: 1%/wk wks 1–5, 2%/wk from wk 6, cap 15% of delayed item (Vertiv) · Cummins 1%/mo cap 5% · Trane 1%/wk cap 15% · PH 5/5/5 per-late-unit after 7-day grace | §13 LD (trigger, rate, period bands, cap) | ✗ |
| **Deposits** drive prepurchase exposure; category deposit %, 0% floored to 5%, negotiated toward 0 | §8 Deposit dimension; §10 `deposit_due` | ✗ |
| **Tariff by country of origin**, finished vs semi-finished classification, future exposure beyond baseline | §2 "Tariff — country-of-origin exposure" | ✗ flat `tariff_pct` scalar |
| **Index-linked escalation**: Index Link · Index Baseline · Review Period · % of unit price · weighted impact | §2 "Escalation — to the required-by date" | ✗ flat `escalation_pct` scalar |
| **Freight varies by origin** 10× across bids ($2,000 → $20,000) | §2 "Freight — adjusted for origin" | partial (flat `freight_unit`) |
| Losing bids carry written reasons; sourcing has a per-lot narrative | §7 "losing quotes stay in the record… feeds the ROM engine" | partial — retained, no reason field |
| Submittal release gates fabrication; PO form redlines block award | §9 three readiness tracks (`quote` · `po_form` · `design`) | ✗ |
| Vendor ≠ manufacturer (Parrish Hare → GE Prolec / MCI); Factory Country · Factory Location · Integration Location · Sub-Supplier | §11 vendor identity; §19 tariff exposure by origin | ✗ |

## B. Genuinely new — the documents carry it, the spec does not

1. **One-time costs are per-order, not per-unit.** FWT $57,500–$70,000; Owner's Training $10,000 vs
   $2,475. The spec's ROM layers (services · freight · tariff · tax · escalation) are all per-unit or
   percentage. Needs an order-level cost layer that amortizes over the lot — and it prices the
   split-award question directly: **split a lot and you pay FWT twice.**
2. **Technical compliance is a matrix, not a boolean.** The chiller lot levels on eight named specs
   (elevation, sound dBA, −20°F restart, accessory freeze protection, kW/ton power limit, control
   power feeds, integral pump, 4-minute rapid restart) with Comply/Deviate **plus evidence text** per
   bid. Spec §8 has only "Design — whether their submittal is accepted." Deviations were the ruling
   factor in 5 of 6 bids.
3. **Cross-lot spec dependency.** "Due to limited generator capacity, target ACC power input is
   1.05 kW/Ton." A chiller at 1.44 kW/ton forces more generator and UPS. One lot's spec changes
   another lot's quantity. Nothing in the model links lots.
4. **Add/alts and equalizing adders.** Priced-but-unselected options (2nd-yr warranty, 95% PFC $34,400,
   hail guards $25,920, IEEE filter $67,800, enclosure 80 dBA $35k / 75 dBA $60k) and scope bought
   *into* a cheap bid to make it comparable (pump skid $75,000; integral pump package $26,890).
5. **Budget waterfall with Transfers and Holds.** The award memo reconciles
   Budget $80,532,832 → Transfers $0 → **Holds ($4,163,322 unbought scope: on-site QA/QC, in-factory
   third-party testing, temporary storage)** → Budget after $76,369,510 → Contract award $76,369,510 →
   **(Savings)/Overrun $0.** The BBS "Building ACR" tab carries the same four columns per equipment
   line: **Budget · Committed · To Be Bought · Holds.** Spec has ROM-as-budget and §22 net change, but
   no budget object with transfers and holds. This is the cost-reconciliation wedge's actual arithmetic.
6. **Approval is an artifact, in three forms.** (a) E2 sign-off tab: Name · Team · Function · Sign-Off
   Date across Procurement, Electrical Design, Mechanical Design, Schedule. (b) The award memo's
   six-executive signature block with digital signature IDs. (c) The COAP log: Current Step ·
   Responsible Actor · **Step Age in days** — with a $986,495 change order sitting **140 days**.
   This is the answer to "confirmed at higher levels": recordable now, enforceable only with a
   user/role model that does not exist (single shared API key).
7. **Sourcing mode.** Rapid (≈2 trusted suppliers per category, lead time prioritized) vs
   Standard/BOD (**minimum 4 suppliers per equipment type**, design options, VA/VE, factory visits,
   **multiple award scenario options**). Mode sets the minimum bid count a lot needs to be awardable.
8. **LOI between award and PO.** Governance folder `02 LOI — signed letter of intent, precursor to PO`;
   generators: "LOI released and manufacturing spots secured." Spec §10 goes award → AGREEMENT directly.
9. **Stage Gate 1 / Gate 2.** Gate 1 closes on: PO signed and sent · Active Vendor structure activated ·
   Vendor Checklist populated · post-PO team formally alerted. Gate 2 (FWT vs shipment) is **explicitly
   undecided in the governance document** — model as `awaiting-governance`, do not invent a resolution.
10. **Pre-PO is equipment-keyed; post-PO is vendor-keyed.** The governance folder structure pivots at PO
    signature: sourcing batches *by equipment type*, Active Vendors activates *per vendor* and splits by
    equipment underneath. This is the lot-vs-commercial-bundle boundary, already Related's own structure.
11. **$/MW IT is the project denominator.** OFCI Summary: $3,399,173/MW actual vs $4,048,585/MW budget
    across 88 MW ($299.1M vs $356.3M). Per-equipment denominators are the mechanism; $/MW IT is the
    number an owner quotes. Not specified anywhere.
12. **Split sourcing is already in the tracker.** The BBS "Building ACR" tab has **Supplier 1 and
    Supplier 2 columns per equipment line.** Confirmed independently by the corpus: 4 of 31 executed
    spec-pairs have two suppliers for the same physics (padmounts at 1.60× spread, mech padmounts 2.30×).
13. **Alternates from one vendor.** Texas Air bid two chiller models, Vertiv bid two — six bids from four
    suppliers. The model holds them as unrelated quotes.
14. **Terms are benchmark-rated.** Payment / Cancellation / LD each scored **Better · Average · Below**
    with "Explanation If Below". Close to §13 `is_deviation` + `deviation_reason`, but a three-point
    scale against a house benchmark, not a binary.
15. **Unit identity is a composite code, and one live tag embeds the vendor.** `C1.DH130.1M` =
    building · data hall · equipment · suffix, alongside `ACR Number`, `FO?` (first-of-kind, cf. the
    Normalization Addendum), and a **Gryps Equipment Tag** reading
    `Core-Parrish Hare-Padmount Transformer` — an identifier that breaks the moment you re-source.
    Evidence for why identity must never embed supplier.

## C. Corrections to what plans 09–10 shipped

1. **`leveling()` extends linearly and shouldn't.** `extended = unit_price × total_qty` is wrong once
   order-level costs exist. Needs `Σ(unit × qty) + one_time + services + freight − discount`, with the
   effective per-unit figure amortizing one-time cost over the lot. This is a correctness bug today,
   not a future feature.
2. ~~**Rename `sourcing_package` → `solicitation`** to match spec §7.~~ **Withdrawn on implementation.**
   The spec's `SOLICITATION` carries *issuance* semantics — `invited_vendors[]`, `issued_date`,
   `response_due` — i.e. the act of going to market. `sourcing_package` is the *lot*: a grouping of
   demand on physics. They coincide today only because we happen to solicit one lot at a time.
   Related's own governance keeps them apart too: the sourcing-level unit is an **Equipment Template**
   folder (batched by equipment type) with **Bid Leveling** *inside* it. Renaming would conflate a
   grouping with an event, and would block the obvious next step — one solicitation covering several
   lots to one vendor, which is how cross-lot bundling arrives. Keep `sourcing_package`; add
   `SOLICITATION` as a separate object in Packet 3 with `invited_vendors[] · issued_date ·
   response_due`, pointing at one or more packages.

   The genuine divergence still stands and the documents win: the spec puts `demand_line_id` on
   `QUOTE` (bid per line), while the Cheyenne sheet takes **one bid for the lot** and the award memo
   **allocates per building afterward** (Exhibit A: A|B|S|C|D|House with % per building). Bid at lot
   level, allocate at award — which is what `award_package()` already does. Amend the spec, not the code.
3. **`quote` has no `disposition_reason`.** Spec §7 says losing quotes are market data; every ruled-out
   bid in the real sheet carries a written reason, and none of it is capturable.

4. **Freeze scope: `system` dropped, `area` added — spec §3 amended.** §3 says
   `scope → project | building | system`, on the rationale that freeze is *"partial where design
   releases in parts."* Working through what a "system" would be, there was no definition that
   survived: HAC is a `sub_type` in the taxonomy (equipment, not a system); E/M skids are either
   equipment types or design groupings depending on whether they're bought assembled; a discipline
   axis would need a column on `equipment_type` and a classification call on six design terms
   (`CMBX CTLH NGE SA SGENC SST TST`) that can't be read from the code. Meanwhile the case it was
   meant to serve — grouping equipment to price to one vendor — **is already served by bid packages,
   at the sourcing layer where it belongs.** A system axis would have put a commercial grouping
   inside a design gate.

   So the scope axis is now exactly the project's location legend: `project | building | area`.
   Design releases by place; who supplies it is a separate question answered later.

   Two consequences, both built: `freeze_event.scope_ref` records **which** building or area
   (`scope='building'` with no building was an incomplete record — you couldn't answer "was C1
   frozen?"), and **scope now selects the lines** instead of labelling a hand-picked set. Freeze
   takes no `line_ids`; `GET /freeze/preview` shows what a scope would lock, and `POST /freeze`
   resolves the same query. Hand-picking a subset and calling it a "building freeze" was a lie the
   old UI allowed.

## D. Sequence

**Packet 1 — leveling truth (small, corrective) — EXECUTED (migration `0006`)**
Cost layers on `quote` (`services_unit · freight_unit · discount_unit · one_time_cost`) · `bid_layers()`
and `effective_unit()` · leveling normalizes and extends the **all-in**, not the equipment price ·
one-time cost amortizes over the lot · award commits the all-in figure · `decline_quote()` with a
required reason, and declined bids stay as market data without setting the benchmark.
Verified against the real Cheyenne chiller lot: all three bids' all-in unit prices and extended totals
reproduce the sheet exactly ($550,053 / $625,877 / $761,315; $46.20M / $52.57M / $63.95M).
Rename withdrawn — see Corrections §2.

**Packet 2 — the clock at sourcing (§5/§6, highest leverage)**
`LEAD_TIME_BASELINE` / `CONDITION_ADJUSTMENT` / `VENDOR_OVERRIDE` with provenance · `required_po_date`
triggers · delivery cadence per period on both demand and quote · Need-by/Commit first-gear and
last-gear. This is where P6 actually attaches, and it is fully specified already.

**Packet 3 — awardability (§8/§9 + new B2)**
Technical compliance matrix with evidence · three readiness tracks · minimum-bid-count by sourcing mode ·
award blocked with the reason visible rather than cheapest-wins.

**Packet 4 — exposure (§13/§15 + new B5)**
Term registry with cancellation ladder, LD formulas, payment shapes · deposit at award · benchmark
rating · budget object with Transfers / Holds / To-Be-Bought → (Savings)/Overrun.

**Packet 5 — allocation and instruments**
Split award across vendors with a coverage invariant (Σ scope-line qty ≤ demand qty) · LOI as a state
between award and PO · Gate 1 checklist · commercial bundle (one vendor, N lots, one PO).

**Packet 6 — rollup**
$/MW IT at project level · surplus/shortfall from Budget vs Committed vs To-Be-Bought.

## E. Explicitly not building
- **Gate 2 resolution.** Related hasn't decided FWT-vs-shipment. Model the state, not an answer.
- **The 100%-tracking / 95%-sync / <2%-warranty targets.** The findings review confirms these appear in
  roadmap decks and in **none** of the executed Accenture SOWs. They are the KPI layer Viasel makes
  measurable, not thresholds to enforce.
- **A permission model.** Record who signed and when; do not pretend to authorize until there are users.
- **Tuning to Cheyenne/Mitten/Spade numbers.** Sample fuel, per the standing convention.

# Viasel Legend — Expansion Candidates (for review)

**Status:** candidates, NOT fact. Diffed the clean **Exhibits Legend** against the Spade/Mitten data in `ofci data`.
You own final naming/codes.

## Why the data looks messy (and why that's the point)

The names like *"CMDA Transformer," "MNR UPS," "Padmount Transformer – Mech"* mix things that don't belong in a
type name. That happened because these were a **first run** — first-of-kind units got tagged with the location
they were assigned to, or analysts just carried the location/vendor into the name by habit. **The team already
admitted this: baking vendor (and location) into the naming convention was a lesson-learned.** Viasel's job is to
enforce that lesson *structurally*, so it can't happen again.

## The rule — the type name is PHYSICS ONLY; everything else is an attribute

| Axis | Belongs in the name? | Where it lives | Examples |
|---|---|---|---|
| **Equipment Type** (what it is + how it's measured) | ✅ yes — canonical | the Legend | Padmount Transformer ($/kVA), Power Transformer ($/MVA) |
| **Location** | ❌ no | crosswalk (per-project) | Compute, Mech, Spine, House, Core, Ops, Exterior, **MNR**, **CMDA**, Substation, Yard |
| **Vendor / OEM** | ❌ no | attribute | Eaton, GE Prolec, Vertiv, Boyd, Kais Air, Parrish Hare |
| **Phase / Dev Agreement** | ❌ no | attribute | DA1, DA2, CO-to-DA1 |
| **First-of-kind** | ❌ no | **cost flag**, not a type | first unit carries NRE/tooling; one-time cost, same type |

> Differs in **what it physically is / how it's measured** → new **type**. Differs in **where it sits, who made it, which phase, or whether it's the first one** → **attribute**, not a new type.

So `CMDA Transformer` = `Padmount Transformer @ 3250kVA` **@** location `CMDA`, **vendor** GE Prolec, **first-of-kind** = true. One type, four attributes. **First-of-kind matters for cost, not identity** — the ROM captures its NRE as a one-time adder and can normalize it out so the base $/kVA compares apples-to-apples with the repeat units.

---

## A. New sub-types for EXISTING design terms (vendor + location stripped)

| Design Term | Unit Type Code | New sub-type | Denominator | Legend has |
|---|---|---|---|---|
| CHLR | Air-Cooled Chiller | **500 Ton**, **850 Ton** (mag-bearing) | $/ton | 350, 535 |
| GEN | Generator | **500kW** | $/kW | 1250, 3000kW |
| H GEN | House Generator | **500kW** | $/kW | 1000kW |
| XFMR | Padmount Transformer | **3200kVA** | $/kVA | 3000/3250/5000 |
| XFMR | House Transformer | **500kVA** | $/kVA | 750/1000 |
| UPS | UPS | **200kW** (3min), **2000kW** (8min) | $/kW | 2.25MW/2MW/750kW |
| CRAH | CRAH | **112kW**, **211kW** | $/kW | 255, 75kW |
| CRAH | Fan Wall | **700kW** (98k CFM) | $/kW | 500/550kW |
| CRAC | Computer Room A/C | **230kW Dx** (50k CFM) | $/kW | — |
| PDU | PDU | **75kVA** | $/kVA | 1MW/2MW |
| PDU | Busway | **40/50ft 400A**, **96ft 3000A** | $/ft | — |
| CRAH | HAC | **50ft "Brooklyn Lite"** | $/ft | SFN #2 |
| SWGR | MV Switchgear | **2500A Metalclad** | $/unit | 34.5kV |
| SWBD | LV Switchboard | **3200A 415V** | $/A | 480/277V |
| TST | Thermal (Pump) Skid | **8" / 3000 gal TES** | $/unit | tanks |

---

## B. New equipment TYPES — location-agnostic (currently missing)

The high-voltage units that sit in the substation. **"Substation" is a *location*, not a type** — it goes in the
Location axis. These are real new *types*, priced the same wherever they sit.

| Suggested Design Term | Unit Type Code | Example spec | Denominator (candidate) |
|---|---|---|---|
| PXFMR | Power Transformer | 360MVA, 345–34.5kV | **$/MVA** |
| HVSWGR | HV Distribution Switchgear | 34.5/38kV, 3ph 3w | $/unit |
| CB | Circuit Breaker | 345kV | $/unit |
| DSW | Disconnect Switch | 345kV | $/unit |
| SA | Surge Arrestor | 345kV | $/unit |
| CVT | Coupling Voltage Transformer | 345kV | $/unit |
| CAP | Capacitor Bank | 34.5kV | $/unit |
| CLR | Current Limiting Reactor | 34.5kV | $/unit |
| SST | Station Service Transformer | — | $/kVA |
| CMBX | Combined Transformer | — | $/MVA |
| NGE | Neutral Grounding Equipment | 34.5kV | $/unit |
| SGENC | Switchgear Enclosure | — | $/unit |
| CTLH | Control House | — | $/unit |

---

## C. Attributes pulled OUT of type names (for the crosswalk / line, not the Legend)

- **Location:** Base, Compute, Mech, Spine, House, Core, Ops, Exterior, MNR, CMDA, Substation, Yard → per-project crosswalk → small canonical location-kind vocab (Data Hall · Central Plant · Substation · Yard · Ops · Exterior).
- **Vendor / OEM:** Eaton, GE Prolec, Vertiv, Boyd, Kais Air, Parrish Hare, Powell, MCI, Trane, Cummins → vendor master.
- **Phase / Dev Agreement:** DA1, DA2, CO-to-DA1 → line attribute.
- **First-of-kind:** boolean flag + one-time NRE cost on the line → never a type.

*Candidates v3 — type = physics only; location / vendor / phase / first-of-kind are attributes. This is the structural version of the naming lesson the analysts already learned. Confirm / rename, then A+B become canonical Legend entries and C feeds the crosswalk + vendor master.*

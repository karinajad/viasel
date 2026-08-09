# ROM reconciliation spike — reads sample executed prices, proves normalization reconciles,
# and shows normalized cross-vendor comparables (the ROM's whole value).
import csv, collections
rows=[dict(r) for r in csv.DictReader(open('executed_scope_lines.csv'))]
def f(x):
    try: return float(x)
    except: return None

# ---- 1. Reconciliation: does (base+services)*(1+tax) reproduce reported all-in? ----
ex=[r for r in rows if r['status'].lower().startswith('exec') and f(r['allin_reported']) and f(r['base_unit'])]
def pct_err(r):
    rep=f(r['allin_reported']); calc=f(r['allin_calc'])
    return abs(rep-calc)/rep*100 if rep else None
w01=[r for r in ex if pct_err(r)<0.1]
w1 =[r for r in ex if pct_err(r)<1.0]
print(f"RECONCILIATION  (executed rows: {len(ex)})")
print(f"  within 0.1% of the hand-built all-in : {len(w01)}/{len(ex)}")
print(f"  within 1.0%                          : {len(w1)}/{len(ex)}")
worst=sorted(ex,key=lambda r:-pct_err(r))[:4]
print("  biggest misses (need freight/one-time/first-of-kind layer the sample dropped):")
for r in worst:
    print(f"    {r['etype']:26.26s} {r['spec'][:18]:18s} err {pct_err(r):5.1f}%  (rep ${f(r['allin_reported']):,.0f} vs ${f(r['allin_calc']):,.0f})")

# ---- 2. Normalized comparables: same spec, different vendor -> $/denominator spread ----
print("\nNORMALIZED COMPARABLES  ($ per natural unit — the cross-vendor apples-to-apples)")
g=collections.defaultdict(list)
for r in ex:
    key=(r['etype'],r['spec'].strip(),r['denominator'])
    if f(r['normalized']): g[key].append((r['oem'] or r['supplier'], f(r['normalized'])))
shown=0
for (et,spec,den),vs in g.items():
    if len(vs)>=2:
        vs=sorted(vs,key=lambda x:x[1])
        lo,hi=vs[0][1],vs[-1][1]
        spread=(hi-lo)/lo*100 if lo else 0
        print(f"  {et} · {spec[:22]:22s} {den}")
        for oem,n in vs: print(f"      {oem:20.20s} {n:>10,.2f} {den[2:]}")
        print(f"      -> spread {spread:.0f}%  (leverage: normalize and the cheaper vendor is obvious)")
        shown+=1
if not shown: print("  (no same-spec multi-vendor pairs in this sample slice)")

# ---- 3. Confidence tiers already in the data ----
print("\nCONFIDENCE TIERS (their own tagging = the ROM's confidence axis, free)")
t=collections.Counter(r['status'] for r in rows)
for k,v in t.most_common(): print(f"  {v:3d}  {k}")

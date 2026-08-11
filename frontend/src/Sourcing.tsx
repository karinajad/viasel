import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPost } from './services/api'
import { STATE, count, money, physics, signed, signedPct } from './lib/format'
import type { CandidatesRead, PackageDetail, PackageRead } from './types/sourcing'

const label = (p: { type_query: string; size: number; denominator: string }) =>
  physics(p.type_query, p.size, p.denominator)

export default function SourcingFace({ project }: { project: string }) {
  const candQ = useQuery({
    queryKey: ['candidates', project],
    queryFn: () => apiGet<CandidatesRead>(`/packages/candidates?project=${encodeURIComponent(project)}`),
  })
  const pkgQ = useQuery({
    queryKey: ['packages', project],
    queryFn: () => apiGet<PackageRead[]>(`/packages?project=${encodeURIComponent(project)}`),
  })

  return (
    <div>
      <div className="headline">
        <h2>Sourcing — {project}</h2>
        <span className="pill live">LIVE · Supabase</span>
      </div>
      <p className="desc">
        You don’t buy one transformer at one hall — you buy every transformer of that size on the project as a lot.
        Scope the buy per equipment, take one bid per vendor for the whole lot, level them per the natural unit,
        award once. Only frozen demand is sourceable.
      </p>

      <Candidates project={project} data={candQ.data} loading={candQ.isLoading} error={candQ.isError} />
      <div style={{ marginTop: 16 }}>
        <Packages project={project} packages={(pkgQ.data ?? []).filter((p) => p.state !== 'cancelled')} loading={pkgQ.isLoading} />
      </div>
    </div>
  )
}

function Candidates({ project, data, loading, error }: { project: string; data?: CandidatesRead; loading: boolean; error: boolean }) {
  const qc = useQueryClient()
  const groups = data?.groups ?? []
  const createM = useMutation({
    mutationFn: (ids: string[]) => apiPost<PackageDetail>('/packages', { project_id: project, demand_line_ids: ids }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidates', project] })
      qc.invalidateQueries({ queryKey: ['packages', project] })
    },
  })

  return (
    <div className="card">
      <h4>① Scope the buy — what the frozen demand adds up to</h4>
      {error && <p style={{ color: 'var(--red)' }}>Couldn’t reach the API (backend on :8000, key set?).</p>}
      {loading && <p style={{ color: 'var(--mut)', fontSize: 13 }}>Loading…</p>}
      {!loading && !error && groups.length === 0 && (
        <p style={{ color: 'var(--mut)', fontSize: 13 }}>
          Nothing left to scope. Freeze demand on the <strong>Demand</strong> tab, or see the packages below.
        </p>
      )}
      {groups.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Equipment (one lot)</th>
              <th>Where</th>
              <th className="num">Lines</th>
              <th className="num">Units</th>
              <th className="num">ROM extended</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={`${g.type_query}-${g.size}-${g.denominator}`}>
                <td><strong>{label(g)}</strong></td>
                <td style={{ color: 'var(--mut)' }}>{g.buildings.length ? g.buildings.join(' · ') : 'unassigned'}</td>
                <td className="num">{g.line_count}</td>
                <td className="num">{g.total_qty}</td>
                <td className="num">{money(g.rom_extended)}</td>
                <td className="num">
                  <button className="btn sm" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => createM.mutate(g.demand_line_ids)} disabled={createM.isPending}>
                    Scope as package ▸
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {createM.isError && <div className="note">Couldn’t scope that lot — {String(createM.error)}</div>}
      {!!data?.unpoolable_count && (
        <div className="note">
          {data.unpoolable_count} frozen line{data.unpoolable_count === 1 ? '' : 's'} can’t be pooled — no equipment
          type captured, so there’s no physics to bid against. Price it on the Demand tab and it joins a lot.
        </div>
      )}
    </div>
  )
}

function Packages({ project, packages, loading }: { project: string; packages: PackageRead[]; loading: boolean }) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div className="card">
      <h4>② Bid packages</h4>
      {loading && <p style={{ color: 'var(--mut)', fontSize: 13 }}>Loading…</p>}
      {!loading && packages.length === 0 && (
        <p style={{ color: 'var(--mut)', fontSize: 13 }}>No packages yet — scope a lot above.</p>
      )}
      {packages.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Package</th>
              <th>Equipment</th>
              <th className="num">Units</th>
              <th className="num">ROM extended</th>
              <th className="num">Bids</th>
              <th>State</th>
              <th className="num">Awarded</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {packages.map((p) => (
              <Fragment key={p.id}>
                <tr>
                  <td><strong>{p.code}</strong></td>
                  <td>{label(p)} <span style={{ color: 'var(--mut)' }}>· {p.line_count} lines</span></td>
                  <td className="num">{p.total_qty}</td>
                  <td className="num">{money(p.rom_extended)}</td>
                  <td className="num">{p.quote_count}{p.declined_count > 0 && <span style={{ color: 'var(--mut)', fontSize: 11 }}> +{p.declined_count} out</span>}</td>
                  <td><span className="st" style={{ background: p.state === 'awarded' ? 'var(--accent)' : '#6b7280' }}>{p.state}</span></td>
                  <td className="num">{p.awarded_vendor ? <>{p.awarded_vendor}<br /><span style={{ color: 'var(--mut)', fontSize: 11 }}>{money(p.awarded_extended)}</span></> : '—'}</td>
                  <td className="num">
                    <button className="btn sm" onClick={() => setOpen(open === p.id ? null : p.id)}>
                      {open === p.id ? 'Hide' : p.state === 'awarded' ? 'View ▸' : 'Level bids ▸'}
                    </button>
                  </td>
                </tr>
                {open === p.id && (
                  <tr><td colSpan={8} style={{ background: '#fafbfc' }}><PackagePanel packageId={p.id} project={project} siblings={packages.filter((s) => s.id !== p.id && s.state === 'open' && s.type_query === p.type_query && s.size === p.size && s.denominator === p.denominator)} /></td></tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function PackagePanel({ packageId, project, siblings }: { packageId: string; project: string; siblings: PackageRead[] }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['package', packageId], queryFn: () => apiGet<PackageDetail>(`/packages/${packageId}`) })
  const [vendor, setVendor] = useState('')
  const [oem, setOem] = useState('')
  const [unit, setUnit] = useState<number | ''>('')
  const [lead, setLead] = useState<number | ''>('')
  const [services, setServices] = useState<number | ''>('')
  const [freight, setFreight] = useState<number | ''>('')
  const [discount, setDiscount] = useState<number | ''>('')
  const [oneTime, setOneTime] = useState<number | ''>('')
  const [confirming, setConfirming] = useState<string | null>(null)
  const [declining, setDeclining] = useState<string | null>(null)
  const [declineReason, setDeclineReason] = useState('')
  const [tried, setTried] = useState(false)
  const [openLayers, setOpenLayers] = useState(false)
  const [picked, setPicked] = useState<string[]>([])

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['package', packageId] })
    qc.invalidateQueries({ queryKey: ['packages', project] })
  }
  const num = (v: number | '') => (v === '' ? null : Number(v))
  const numOrBlank = (s: string): number | '' => (s === '' ? '' : Number(s))
  const bidM = useMutation({
    mutationFn: () => apiPost<PackageDetail>(`/packages/${packageId}/quotes`, {
      vendor, oem: oem || null, unit_price: Number(unit), lead_time_weeks: num(lead),
      services_unit: num(services), freight_unit: num(freight),
      discount_unit: num(discount), one_time_cost: num(oneTime),
    }),
    onSuccess: () => {
      setVendor(''); setOem(''); setUnit(''); setLead('')
      setServices(''); setFreight(''); setDiscount(''); setOneTime('')
      setTried(false)
      refresh()
    },
  })
  // a bid needs a vendor and an equipment price to be a bid; everything else is optional.
  // The button stays pressable and says what's missing rather than sitting dead.
  const missing = [!vendor && 'a vendor', unit === '' && 'an equipment $/unit'].filter(Boolean)
  const layerCount = [services, freight, discount, oneTime, oem].filter((v) => v !== '' && v !== null).length
  const declineM = useMutation({
    mutationFn: (quoteId: string) =>
      apiPost(`/packages/${packageId}/quotes/${quoteId}/decline`, { reason: declineReason }),
    onSuccess: () => { setDeclining(null); setDeclineReason(''); refresh() },
  })
  const awardM = useMutation({
    mutationFn: (quoteId: string) => apiPost(`/packages/${packageId}/award`, { quote_id: quoteId }),
    onSuccess: () => { setConfirming(null); refresh(); qc.invalidateQueries({ queryKey: ['demand-lines'] }) },
  })
  const dropM = useMutation({
    mutationFn: (dlId: string) => apiDelete(`/packages/${packageId}/lines/${dlId}`),
    onSuccess: () => { refresh(); qc.invalidateQueries({ queryKey: ['candidates', project] }) },
  })
  const restructure = {
    onSuccess: () => {
      setPicked([])
      refresh()
      qc.invalidateQueries({ queryKey: ['candidates', project] })
    },
  }
  const splitM = useMutation({
    mutationFn: () => apiPost(`/packages/${packageId}/split`, { demand_line_ids: picked }),
    ...restructure,
  })
  const mergeM = useMutation({
    mutationFn: () => apiPost(`/packages/${packageId}/merge-lines`, { demand_line_ids: picked }),
    ...restructure,
  })
  const moveM = useMutation({
    mutationFn: (target: string) => apiPost(`/packages/${target}/lines`, { demand_line_ids: picked }),
    ...restructure,
  })
  const killBidM = useMutation({
    mutationFn: (quoteId: string) => apiDelete(`/packages/${packageId}/quotes/${quoteId}`),
    onSuccess: refresh,
  })
  const restructureError = [splitM.error, mergeM.error, moveM.error, killBidM.error].find(Boolean)

  if (q.isLoading || !q.data) return <div style={{ padding: 8, color: 'var(--mut)', fontSize: 12.5 }}>Loading…</div>
  const { package: pkg, lines, leveling } = q.data
  const awarded = pkg.state === 'awarded'
  const oneLiveBid = leveling.filter((r) => r.state !== 'declined').length < 2
  // preview only — the authoritative figure is effective_unit() in services/packaging.py,
  // computed server-side and returned on save
  const n = (v: number | '') => (v === '' ? 0 : Number(v))
  const previewAllIn =
    n(unit) + n(services) + n(freight) - n(discount) + (pkg.total_qty ? n(oneTime) / pkg.total_qty : 0)

  return (
    <div style={{ padding: '8px 2px' }}>
      <Sub>Lot contents · {count(pkg.total_qty, 'unit')} of {label(pkg)} across {count(pkg.line_count, 'line')}</Sub>
      <table>
        <thead><tr><th style={{ width: 26 }} /><th>Building / area</th><th className="num">Qty</th><th className="num">ROM / unit</th><th>Demand state</th><th /></tr></thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.demand_line_id}>
              <td>
                {!awarded && (
                  <input type="checkbox" checked={picked.includes(l.demand_line_id)} onChange={() => setPicked((s) => s.includes(l.demand_line_id) ? s.filter((x) => x !== l.demand_line_id) : [...s, l.demand_line_id])} />
                )}
              </td>
              <td>{l.target_building ?? 'unassigned'}{l.target_area ? ` · ${l.target_area}` : ''}</td>
              <td className="num">{l.qty}</td>
              <td className="num">{money(l.rom_unit_price)}</td>
              <td><span className="st" style={{ background: STATE[l.state] ?? '#6b7280' }}>{l.state}</span></td>
              <td className="num">
                {!awarded && lines.length > 1 && (
                  <button className="btn sm danger" title="return to the candidate pool" onClick={() => dropM.mutate(l.demand_line_id)} disabled={dropM.isPending}>✕</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {!awarded && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', margin: '8px 0 14px', minHeight: 26 }}>
          {picked.length === 0 ? (
            <span style={{ fontSize: 11, color: '#9aa0a6' }}>
              Tick lines to split them out, move them into another lot of the same equipment, or merge duplicates.
            </span>
          ) : (
            <>
              <span style={{ fontSize: 12, color: 'var(--mut)' }}>{count(picked.length, 'line')} selected</span>
              <button className="btn sm" onClick={() => splitM.mutate()} disabled={splitM.isPending || picked.length === lines.length}
                title={picked.length === lines.length ? 'that is every line — it would just rename the lot' : 'break these out into a new lot'}>
                Split out ▸
              </button>
              {siblings.length > 0 && (
                <select className="si" defaultValue="" onChange={(e) => { if (e.target.value) moveM.mutate(e.target.value) }} disabled={moveM.isPending}>
                  <option value="">Move into…</option>
                  {siblings.map((s) => <option key={s.id} value={s.id}>{s.code} ({count(s.total_qty, 'unit')})</option>)}
                </select>
              )}
              {picked.length > 1 && (
                <button className="btn sm" onClick={() => mergeM.mutate()} disabled={mergeM.isPending}
                  title="consolidate duplicates — same building and area only">
                  Merge duplicates
                </button>
              )}
              <button className="btn sm" onClick={() => setPicked([])}>Clear</button>
            </>
          )}
        </div>
      )}
      {restructureError && <div className="note" style={{ marginTop: 0 }}>{String(restructureError).replace(/^Error:\s*/, '')}</div>}

      <Sub>
        Bid leveling · every bid all-in, per {pkg.denominator}
        {pkg.rom_unit_price != null
          ? <>, against the {money(pkg.rom_unit_price)}/unit the record already says</>
          : <> · no ROM on these lines, so there’s nothing to compare against yet</>}
      </Sub>
      {!awarded && (
        <div className="bidform">
          <div className="row">
            <Field label="Vendor" required width={168}>
              <input className="si" value={vendor} onChange={(e) => setVendor(e.target.value)} />
            </Field>
            <Field label={`Equipment $ / unit`} required width={150}>
              <input className="si" type="number" value={unit} onChange={(e) => setUnit(numOrBlank(e.target.value))} />
            </Field>
            <Field label="Lead time (weeks)" width={124}>
              <input className="si" type="number" value={lead} onChange={(e) => setLead(numOrBlank(e.target.value))} />
            </Field>
            <div style={{ flex: 1 }} />
            <AllIn allIn={previewAllIn} qty={pkg.total_qty} ready={unit !== ''} />
          </div>

          <button type="button" className="disc" onClick={() => setOpenLayers(!openLayers)}>
            {openLayers ? '▾' : '▸'} Other cost layers
            {!openLayers && layerCount > 0 && <span className="badge">{layerCount}</span>}
            {!openLayers && layerCount === 0 && <span className="hint">optional — services, freight, discount, one-time, OEM</span>}
          </button>

          {openLayers && (
            <div className="row layers">
              <Field label="Services $ / unit" hint="startup · commissioning · IST · warranty" width={140}>
                <input className="si" type="number" value={services} onChange={(e) => setServices(numOrBlank(e.target.value))} />
              </Field>
              <Field label="Freight $ / unit" width={124}>
                <input className="si" type="number" value={freight} onChange={(e) => setFreight(numOrBlank(e.target.value))} />
              </Field>
              <Field label="Discount $ / unit" hint="subtracted" width={132}>
                <input className="si" type="number" value={discount} onChange={(e) => setDiscount(numOrBlank(e.target.value))} />
              </Field>
              <Field
                label="One-time $"
                hint={pkg.total_qty === 1 ? 'whole order — this lot is one unit' : `whole order — spread over ${pkg.total_qty}`}
                width={140}
              >
                <input className="si" type="number" value={oneTime} onChange={(e) => setOneTime(numOrBlank(e.target.value))} />
              </Field>
              <Field label="OEM" hint="if not the vendor" width={150}>
                <input className="si" value={oem} onChange={(e) => setOem(e.target.value)} />
              </Field>
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10 }}>
            <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }} onClick={() => { setTried(true); if (missing.length === 0) bidM.mutate() }} disabled={bidM.isPending}>
              {bidM.isPending ? 'Adding…' : 'Add bid'}
            </button>
            {tried && missing.length > 0 && (
              <span style={{ fontSize: 12, color: 'var(--red)' }}>Needs {missing.join(' and ')}.</span>
            )}
          </div>
        </div>
      )}

      {leveling.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No bids yet.</div>}
      {leveling.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Vendor</th>
              <th className="num">All-in $ / unit</th>
              <th className="num">per {pkg.denominator}</th>
              <th className="num">Lead</th>
              <th className="num">Extended ({pkg.total_qty})</th>
              <th className="num">{oneLiveBid ? '' : 'vs lowest'}</th>
              <th className="num">vs ROM</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {leveling.map((r) => {
              const out = r.state === 'declined'
              return (
              <tr key={r.quote_id} style={{ background: r.is_selected ? '#eef7f0' : 'transparent', opacity: out ? 0.55 : 1 }}>
                <td>
                  <strong style={{ textDecoration: out ? 'line-through' : 'none' }}>{r.vendor}</strong>
                  {r.oem && <span style={{ color: 'var(--mut)' }}> · {r.oem}</span>}
                  {r.is_low && !awarded && !oneLiveBid && <span style={{ color: 'var(--accent)', fontSize: 11 }}> · lowest awardable</span>}
                  {r.is_selected && <span style={{ color: 'var(--accent)', fontSize: 11, fontWeight: 600 }}> · awarded</span>}
                  <div style={{ fontSize: 10.5, color: '#9aa0a6', fontVariantNumeric: 'tabular-nums' }}>
                    equip {money(r.layers.equipment)}
                    {!!r.layers.services && <> · svc {money(r.layers.services)}</>}
                    {!!r.layers.freight && <> · frt {money(r.layers.freight)}</>}
                    {!!r.layers.discount && <> · disc {money(r.layers.discount)}</>}
                    {!!r.layers.one_time_total && <> · one-time {money(r.layers.one_time_total)} ÷ {pkg.total_qty} = {money(r.layers.one_time_amortized)}</>}
                  </div>
                  {out && r.disposition_reason && (
                    <div style={{ fontSize: 11, color: 'var(--red)' }}>ruled out — {r.disposition_reason}</div>
                  )}
                </td>
                <td className="num"><strong>{money(r.effective_unit)}</strong></td>
                <td className="num">{money(r.normalized)}</td>
                <td className="num">{r.lead_time_weeks ?? '—'}</td>
                <td className="num">{money(r.extended)}</td>
                <td className="num" style={{ color: 'var(--mut)' }}>
                  {oneLiveBid || r.delta_vs_low === 0 ? '—' : `${signed(r.delta_vs_low)}${signedPct(r.delta_vs_low_pct)}`}
                </td>
                <td className="num" style={{ color: r.delta_vs_rom == null ? 'var(--mut)' : r.delta_vs_rom > 0 ? 'var(--red)' : 'var(--accent)' }}>
                  {r.delta_vs_rom == null ? '—' : `${signed(r.delta_vs_rom)}${signedPct(r.delta_vs_rom_pct)}`}
                </td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  {!awarded && !out && confirming !== r.quote_id && declining !== r.quote_id && (
                    <>
                      <button className="btn sm" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => setConfirming(r.quote_id)}>Award ▸</button>{' '}
                      <button className="btn sm" title="rule this bid out — it stays on the record" onClick={() => setDeclining(r.quote_id)}>Rule out</button>{' '}
                      <button className="btn sm danger" title="delete this bid entirely — needed before the lot can be restructured" onClick={() => killBidM.mutate(r.quote_id)} disabled={killBidM.isPending}>Delete</button>
                    </>
                  )}
                  {!awarded && confirming === r.quote_id && (
                    <>
                      <button className="btn sm pri" onClick={() => awardM.mutate(r.quote_id)} disabled={awardM.isPending}>
                        {awardM.isPending ? 'Awarding…' : `Commit ${money(r.extended)}`}
                      </button>{' '}
                      <button className="btn sm" onClick={() => setConfirming(null)}>Cancel</button>
                    </>
                  )}
                  {declining === r.quote_id && (
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <input className="si" style={{ width: 190 }} autoFocus placeholder="reason it's ruled out…" value={declineReason} onChange={(e) => setDeclineReason(e.target.value)} />
                      <button className="btn sm danger" onClick={() => declineM.mutate(r.quote_id)} disabled={!declineReason || declineM.isPending}>Rule out</button>
                      <button className="btn sm" onClick={() => { setDeclining(null); setDeclineReason('') }}>Cancel</button>
                    </div>
                  )}
                </td>
              </tr>
            )})}
          </tbody>
        </table>
      )}

      {confirming && !awarded && (
        <div className="note">
          Awarding commits supply for all {pkg.total_qty} units — every unit’s own record gets a scope line matched to
          its demand line, and the demand moves to <strong>matched</strong>. Reopening it needs a thaw with a reason.
        </div>
      )}
      {awarded && (
        <div className="note">
          Awarded to <strong>{pkg.awarded_vendor}</strong> · {money(pkg.awarded_extended)} committed across {pkg.line_count} lines
          {pkg.rom_extended != null && pkg.awarded_extended != null && (
            <> · {signed(pkg.awarded_extended - pkg.rom_extended)} vs the ROM the record carried</>
          )}
          .
        </div>
      )}
      {leveling.some((r) => r.state === 'declined') && (
        <div style={{ fontSize: 11, color: '#9aa0a6', marginTop: 6 }}>
          Ruled-out bids stay on the record — a price you rejected is as informative as one you paid, and it
          still feeds the ROM. They don’t set the benchmark, so a negative “vs lowest” is what compliance costs.
        </div>
      )}
      {bidM.isError && <div className="note">Couldn’t add that bid — {String(bidM.error)}</div>}
      {awardM.isError && <div className="note">Couldn’t award — {String(awardM.error)}</div>}
      {declineM.isError && <div className="note">Couldn’t rule that bid out — {String(declineM.error)}</div>}
    </div>
  )
}

function Sub({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)', marginBottom: 6 }}>
      {children}
    </div>
  )
}

/** A labelled input. Labels sit above the box so nothing truncates its own name. */
function Field({ label, children, width, required, hint }: {
  label: string; children: React.ReactNode; width: number; required?: boolean; hint?: string
}) {
  return (
    <div style={{ width }}>
      <label style={{ margin: '0 0 3px' }}>
        {label}{required && <span style={{ color: 'var(--red)' }}> *</span>}
      </label>
      {children}
      {hint && <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 2, lineHeight: 1.3 }}>{hint}</div>}
    </div>
  )
}

/** The number the bid is actually leveled on, while you type it. */
function AllIn({ allIn, qty, ready }: { allIn: number; qty: number; ready: boolean }) {
  return (
    <div style={{ textAlign: 'right', minWidth: 170 }}>
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)' }}>
        all-in / unit
      </div>
      <div style={{ fontSize: 19, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: ready ? 'var(--ink)' : 'var(--line)' }}>
        {ready ? money(allIn) : '—'}
      </div>
      <div style={{ fontSize: 10.5, color: 'var(--mut)' }}>
        {ready ? <>{money(allIn * qty)} for {count(qty, 'unit')}</> : `this is what bids are compared on`}
      </div>
    </div>
  )
}

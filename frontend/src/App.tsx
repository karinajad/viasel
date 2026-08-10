import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from './services/api'
import type { DemandLineRow, EquipmentType, Quote, RomBand, RomPriceRequest } from './types/rom'

const money = (n: number | null): string => (n == null ? '—' : '$' + Math.round(n).toLocaleString())
const parseSize = (s: string): number | null => { const m = s.match(/(\d+(?:\.\d+)?)/); return m ? Number(m[1]) : null }
const TIER: Record<string, string> = { high: '#2f6f4f', medium: '#b7791f', low: '#b23a3a', none: '#6b7280' }
const STATE: Record<string, string> = { drafted: '#6b7280', frozen: '#2f6f4f', thawed: '#b23a3a', matching: '#b7791f', matched: '#2f6f4f', satisfied: '#2f6f4f', cancelled: '#9aa0a6' }
const describe = (d: DemandLineRow) => { const a = d.spec_attributes ?? {}; return `${String(a.type_query ?? '')} ${String(a.size ?? '')}${String(a.denominator ?? '').replace('$/', ' ')}`.trim() }

const STOPS = [
  ['DEMAND', 1], ['SOURCING', 1], ['AGREEMENT', 0], ['PRODUCTION', 0],
  ['CUSTODY', 0], ['HANDOVER', 0], ['OPERATION', 0], ['DISPOSITION', 0],
] as const
const TABS = [
  { k: 'demand', label: 'Demand', live: true },
  { k: 'sourcing', label: 'Sourcing', live: true },
  { k: 'cost', label: 'Cost' }, { k: 'logistics', label: 'Logistics' },
  { k: 'vendor', label: 'Vendor' }, { k: 'ops', label: 'Operations' },
  { k: 'disposition', label: 'Disposition' }, { k: 'program', label: 'Program' },
]

export default function App() {
  const [project, setProject] = useState('DEMO')
  const [tab, setTab] = useState('demand')
  const projectsQ = useQuery({ queryKey: ['projects'], queryFn: () => apiGet<string[]>('/projects') })
  const projects = projectsQ.data ?? []
  return (
    <div className="wrap">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1>Viasel</h1>
        <label style={{ fontSize: 12, color: 'var(--mut)' }}>Project&nbsp;
          <input className="si" style={{ width: 160 }} list="projects" value={project} onChange={(e) => setProject(e.target.value)} placeholder="pick or type new" />
          <datalist id="projects">{projects.map((p) => <option key={p} value={p} />)}</datalist>
        </label>
      </div>
      <p className="sub">One record per unit — priced from history, frozen, sourced, awarded.</p>

      <div className="road">
        {STOPS.map(([name, done]) => <div key={name} className={`stop${done ? ' here' : ''}`}><span className="dot" /><b>{name}</b></div>)}
      </div>
      <p className="roadnote">Each unit travels this road. The green stops are live; the rest are the roadmap.</p>

      <div className="tabs">
        {TABS.map((t) => <div key={t.k} className={`tab${tab === t.k ? ' active' : ''}`} onClick={() => setTab(t.k)}>{t.live && <span className="star">★</span>}{t.label}</div>)}
      </div>

      {tab === 'demand' && <DemandFace project={project} />}
      {tab === 'sourcing' && <SourcingFace project={project} />}
      {tab === 'cost' && <Preview title="Cost / Finance — Reconciliation" phase="Phase 2 · the wedge" body="Committed vs. actual and exposure compute themselves and drill to the unit." mock="[ committed-vs-actual by cost code · every row drills to a unit ]" note="Catches the $1.279M gap across 52 executed POs/COs that took weeks to find by hand." />}
      {tab === 'logistics' && <Preview title="Logistics / Custody" phase="Phase 3" body="Every unit's location — factory · transit · warehouse · staged · installed — with exceptions flagged." mock="[ where-is-everything board · phone scan: receive · condition · zone ]" />}
      {tab === 'vendor' && <Preview title="Vendor portal" phase="later" body="Report production stage, upload test reports & serials, mark shipped." mock="[ your scope · report status ]" note="Submitting = getting paid faster; ends four people chasing status." />}
      {tab === 'ops' && <Preview title="Operations — Live Health" phase="Phase 4" body="Each unit green/yellow/red vs. its own day-zero baseline; one plain-English digest a day." mock="[ fleet health · '3 units drifting — UPS-07 battery trending warm' ]" />}
      {tab === 'disposition' && <Preview title="Disposition — the passport" phase="Phase 4" body="Scan a unit → its whole life on one page. Transfer hands the record to the next owner." mock="[ biography: spec · price · changes · storage · service · health ]" />}
      {tab === 'program' && <Preview title="Program — the rollup" phase="later" body="Across projects: covered · pending procurement · at risk · surplus vs. shortfall — every number drills to a line." mock="[ demand fulfillment by freeze set · net change by type ]" />}
    </div>
  )
}

function Preview({ title, phase, body, mock, note }: { title: string; phase: string; body: string; mock: string; note?: string }) {
  return (
    <div>
      <div className="headline"><h2>{title}</h2><span className="pill">{phase}</span></div>
      <p className="desc">{body}</p>
      <div className="card"><div className="ph">{mock}</div>{note && <div className="note">{note}</div>}</div>
    </div>
  )
}

function DemandFace({ project }: { project: string }) {
  const qc = useQueryClient()
  const typesQ = useQuery({ queryKey: ['equipment-types'], queryFn: () => apiGet<EquipmentType[]>('/equipment-types') })
  const types = typesQ.data ?? []
  const unitCodes = [...new Set(types.map((t) => t.unit_type_code))].sort()
  const subsFor = (c: string) => types.filter((t) => t.unit_type_code === c && t.sub_type).map((t) => t.sub_type as string)
  const rowFor = (c: string, s: string) => types.find((t) => t.unit_type_code === c && (s ? t.sub_type === s : true)) ?? types.find((t) => t.unit_type_code === c)

  const [type, setType] = useState('Padmount Transformer')
  const [sub, setSub] = useState('')
  const [qty, setQty] = useState(12)
  const [building, setBuilding] = useState('')
  const [area, setArea] = useState('')
  const subs = subsFor(type)
  const effSub = sub || subs[0] || ''
  const size = parseSize(effSub) ?? 1
  const row = rowFor(type, effSub)
  const denom = row?.natural_denominator ?? '$/unit'

  const priceM = useMutation({ mutationFn: (r: RomPriceRequest) => apiPost<RomBand>('/rom/price', r) })
  const band = priceM.data
  const saveM = useMutation({
    mutationFn: () => apiPost<DemandLineRow>('/demand-lines', {
      project_id: project, qty: Number(qty), equipment_type_id: row?.id ?? null,
      spec_attributes: { type_query: type, denominator: denom, size, sub: effSub },
      target_building: building || null, target_area: area || null,
      rom_unit_price: band?.unit_mid ?? null, rom_confidence: band?.confidence_tier ?? null, rom_comparables_count: band?.comparables_count ?? null,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['demand-lines'] }),
  })

  return (
    <div>
      <div className="headline"><h2>Demand Management — Design &amp; ROM</h2><span className="pill live">LIVE · Supabase</span></div>
      <p className="desc">Price a requirement from executed history, save it as demand, freeze it. No sourcing here — frozen demand flows to the Sourcing face.</p>

      <div className="two">
        <div className="card">
          <h4>① Requirement</h4>
          <label>Equipment type</label>
          <select className="fld" value={type} onChange={(e) => { setType(e.target.value); setSub('') }} disabled={typesQ.isLoading}>
            {typesQ.isLoading && <option>loading…</option>}
            {unitCodes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <label>Size / configuration</label>
          <select className="fld" value={effSub} onChange={(e) => setSub(e.target.value)} disabled={subs.length === 0}>
            {subs.length === 0 && <option value="">— none on record —</option>}
            {subs.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <label>Quantity</label>
          <input className="fld" type="number" value={qty} onChange={(e) => setQty(Number(e.target.value))} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div><label>Building</label><input className="fld" value={building} onChange={(e) => setBuilding(e.target.value)} placeholder="e.g. C1" /></div>
            <div><label>Area / hall</label><input className="fld" value={area} onChange={(e) => setArea(e.target.value)} placeholder="e.g. DH3" /></div>
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--mut)', display: 'flex', gap: 14 }}>
            <span>size <strong className="chip">{size}</strong></span><span>denominator <strong className="chip">{denom}</strong></span>
          </div>
          <div style={{ fontSize: 11, color: '#9aa0a6', marginTop: 4 }}>size &amp; denominator come from the equipment — not typed</div>
          <button className="btn pri" style={{ marginTop: 14, width: '100%' }} onClick={() => priceM.mutate({ type_query: type, denominator: denom, size, qty: Number(qty) })} disabled={priceM.isPending}>{priceM.isPending ? 'Pricing…' : 'Price it'}</button>
        </div>

        <div className="card">
          <h4>② Price band — a byproduct of your history</h4>
          {priceM.isError && <p style={{ color: 'var(--red)' }}>Couldn’t reach the API (backend on :8000, key set?).</p>}
          {!band && !priceM.isError && <p style={{ color: 'var(--mut)' }}>Pick a type and hit “Price it”.</p>}
          {band && (
            <div className="band">
              <div className="nums"><span>{money(band.unit_low)}</span><span className="mid">{money(band.unit_mid)}</span><span>{money(band.unit_high)}</span></div>
              <div className="track" />
              <div style={{ fontSize: 12, color: 'var(--mut)' }}>per unit ({band.denominator}) · extended <strong>{money(band.extended_mid)}</strong> (×{band.qty})</div>
              <div style={{ marginTop: 10, fontSize: 13 }}>Confidence: <strong style={{ color: TIER[band.confidence_tier] }}>{band.confidence_tier}</strong> · {band.comparables_count} comparables</div>
              {band.note && <div className="note">{band.note}</div>}
              <button className="btn" style={{ marginTop: 12, width: '100%', borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => saveM.mutate()} disabled={saveM.isPending || band.unit_mid == null}>{saveM.isPending ? 'Saving…' : 'Save as demand line ▸'}</button>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 16 }}><DemandBoard project={project} /></div>
    </div>
  )
}

function DemandBoard({ project }: { project: string }) {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string[]>([])
  const [scope, setScope] = useState('project')
  const q = useQuery({ queryKey: ['demand-lines', project], queryFn: () => apiGet<DemandLineRow[]>(`/demand-lines?project=${project}`) })
  const lines = q.data ?? []
  const invalidate = () => qc.invalidateQueries({ queryKey: ['demand-lines'] })
  const freezeM = useMutation({ mutationFn: () => apiPost('/freeze', { line_ids: selected, project_id: project, scope, actor: 'web' }), onSuccess: () => { setSelected([]); invalidate() } })
  const thawM = useMutation({ mutationFn: (id: string) => apiPost(`/demand-lines/${id}/thaw`, { reason: null }), onSuccess: invalidate })
  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0 }}>③ Demand board</h4>
        <div style={{ display: 'flex', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--mut)', alignSelf: 'center' }}>freeze as</span>
          <select className="si" value={scope} onChange={(e) => setScope(e.target.value)} title="how much of the design this freeze locks"><option value="project">project</option><option value="building">building</option><option value="system">system</option></select>
          <button className="btn pri sm" onClick={() => freezeM.mutate()} disabled={selected.length === 0 || freezeM.isPending}>Freeze selected ({selected.length})</button>
        </div>
      </div>
      {lines.length === 0 && <p style={{ color: 'var(--mut)', fontSize: 13 }}>No demand yet — price a requirement and save it.</p>}
      {lines.length > 0 && (
        <table style={{ marginTop: 8 }}>
          <thead><tr><th style={{ width: 26 }} /><th>Requirement</th><th>Building</th><th className="num">Qty</th><th className="num">ROM / unit</th><th>Status</th><th /></tr></thead>
          <tbody>
            {lines.map((d) => (
              <tr key={d.id}>
                <td>{d.state === 'drafted' && <input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggle(d.id)} />}</td>
                <td>{describe(d) || '—'}</td>
                <td>{d.target_building ?? '—'}{d.target_area ? ` · ${d.target_area}` : ''}</td>
                <td className="num">{d.qty}</td>
                <td className="num">{money(d.rom_unit_price)}</td>
                <td><span className="st" style={{ background: STATE[d.state] ?? '#6b7280' }}>{d.state}</span></td>
                <td className="num">{(d.state === 'frozen' || d.state === 'matched') && <button className="btn sm danger" onClick={() => thawM.mutate(d.id)} disabled={thawM.isPending}>Thaw</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function SourcingFace({ project }: { project: string }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['demand-lines', project], queryFn: () => apiGet<DemandLineRow[]>(`/demand-lines?project=${project}`) })
  const lines = (q.data ?? []).filter((d) => d.state === 'frozen' || d.state === 'matched')

  return (
    <div>
      <div className="headline"><h2>Sourcing</h2><span className="pill live">LIVE · Supabase</span></div>
      <p className="desc">Frozen demand awaiting supply. Solicit competing quotes, level them per the natural unit, award one — only frozen demand is sourceable.</p>
      <div className="card">
        <h4>Buy list — frozen demand</h4>
        {lines.length === 0 && <p style={{ color: 'var(--mut)', fontSize: 13 }}>Nothing to source yet — freeze a demand line on the <strong>Demand</strong> tab.</p>}
        {lines.length > 0 && (
          <table style={{ marginTop: 8 }}>
            <thead><tr><th>Requirement</th><th>Building</th><th className="num">Qty</th><th className="num">ROM / unit</th><th>Status</th><th /></tr></thead>
            <tbody>
              {lines.map((d) => { const a = d.spec_attributes ?? {}; return (
                <Fragment key={d.id}>
                  <tr>
                    <td>{describe(d) || '—'}</td>
                    <td>{d.target_building ?? '—'}{d.target_area ? ` · ${d.target_area}` : ''}</td>
                    <td className="num">{d.qty}</td>
                    <td className="num">{money(d.rom_unit_price)}</td>
                    <td><span className="st" style={{ background: STATE[d.state] ?? '#6b7280' }}>{d.state}</span></td>
                    <td className="num"><button className="btn sm" onClick={() => setExpanded(expanded === d.id ? null : d.id)}>{expanded === d.id ? 'Hide' : (d.state === 'matched' ? 'View ▸' : 'Source ▸')}</button></td>
                  </tr>
                  {expanded === d.id && <tr><td colSpan={6} style={{ background: '#fafbfc' }}><SourcingPanel demandLineId={d.id} state={d.state} denominator={String(a.denominator ?? '$/unit')} size={Number(a.size ?? 1)} /></td></tr>}
                </Fragment>
              ) })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function SourcingPanel({ demandLineId, state, denominator, size }: { demandLineId: string; state: string; denominator: string; size: number }) {
  const qc = useQueryClient()
  const [vendor, setVendor] = useState('')
  const [unit, setUnit] = useState<number | ''>('')
  const [lead, setLead] = useState<number | ''>('')
  const quotesQ = useQuery({ queryKey: ['quotes', demandLineId], queryFn: () => apiGet<Quote[]>(`/demand-lines/${demandLineId}/quotes`) })
  const quotes = quotesQ.data ?? []
  const awarded = state === 'matched'
  const addM = useMutation({ mutationFn: () => apiPost(`/demand-lines/${demandLineId}/quotes`, { vendor, unit_price: Number(unit), lead_time_weeks: lead === '' ? null : Number(lead), denominator, size }), onSuccess: () => { setVendor(''); setUnit(''); setLead(''); qc.invalidateQueries({ queryKey: ['quotes', demandLineId] }) } })
  const awardM = useMutation({ mutationFn: (id: string) => apiPost(`/demand-lines/${demandLineId}/award`, { quote_id: id }), onSuccess: () => { qc.invalidateQueries({ queryKey: ['quotes', demandLineId] }); qc.invalidateQueries({ queryKey: ['demand-lines'] }) } })
  const norm = (p: number) => (size ? p / size : p)

  return (
    <div style={{ padding: '6px 2px' }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)', marginBottom: 6 }}>Quotes {awarded && '· awarded'} · leveled per {denominator}</div>
      {!awarded && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
          <input className="si" style={{ width: 140 }} placeholder="Vendor" value={vendor} onChange={(e) => setVendor(e.target.value)} />
          <input className="si" style={{ width: 120 }} type="number" placeholder="Unit price" value={unit} onChange={(e) => setUnit(e.target.value === '' ? '' : Number(e.target.value))} />
          <input className="si" style={{ width: 100 }} type="number" placeholder="Lead (wk)" value={lead} onChange={(e) => setLead(e.target.value === '' ? '' : Number(e.target.value))} />
          <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }} onClick={() => addM.mutate()} disabled={!vendor || unit === '' || addM.isPending}>Add quote</button>
        </div>
      )}
      {quotes.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No quotes yet.</div>}
      {quotes.length > 0 && (
        <table>
          <thead><tr><th>Vendor</th><th className="num">Unit price</th><th className="num">Normalized ({denominator})</th><th className="num">Lead (wk)</th><th /></tr></thead>
          <tbody>
            {quotes.map((qt, i) => (
              <tr key={qt.id} style={{ background: qt.state === 'selected' ? '#eef7f0' : 'transparent' }}>
                <td>{qt.vendor}{i === 0 && !awarded && <span style={{ color: 'var(--accent)', fontSize: 11 }}> · lowest</span>}{qt.state === 'selected' && <span style={{ color: 'var(--accent)', fontSize: 11 }}> · awarded</span>}</td>
                <td className="num">{money(qt.unit_price)}</td>
                <td className="num">{money(norm(qt.unit_price))}</td>
                <td className="num">{qt.lead_time_weeks ?? '—'}</td>
                <td className="num">{!awarded && <button className="btn sm" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => awardM.mutate(qt.id)} disabled={awardM.isPending}>Award</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from './services/api'
import type { DemandLineRow, EquipmentType, Quote, RomBand, RomPriceRequest } from './types/rom'

const PROJECT = 'DEMO'

const money = (n: number | null): string =>
  n == null ? '—' : '$' + Math.round(n).toLocaleString()

const parseSize = (s: string): number | null => {
  const m = s.match(/(\d+(?:\.\d+)?)/)
  return m ? Number(m[1]) : null
}

const TIER_COLOR: Record<string, string> = { high: '#2f6f4f', medium: '#b7791f', low: '#b23a3a', none: '#6b7280' }
const STATE_COLOR: Record<string, string> = {
  drafted: '#6b7280', frozen: '#2f6f4f', thawed: '#b23a3a',
  matching: '#b7791f', matched: '#2f6f4f', satisfied: '#2f6f4f', cancelled: '#9aa0a6',
}

const card: React.CSSProperties = { border: '1px solid #c9ccd1', borderRadius: 12, padding: 18 }
const label: React.CSSProperties = { fontSize: 12, color: '#6b7280', margin: '10px 0 4px' }
const field: React.CSSProperties = { width: '100%', padding: '9px 11px', border: '1px solid #c9ccd1', borderRadius: 7, fontSize: 14, background: '#fff' }
const chip: React.CSSProperties = { background: '#eef0f3', padding: '2px 8px', borderRadius: 999 }
const smallInput: React.CSSProperties = { padding: '6px 8px', border: '1px solid #c9ccd1', borderRadius: 6, fontSize: 13 }

function App() {
  const qc = useQueryClient()
  const typesQ = useQuery({ queryKey: ['equipment-types'], queryFn: () => apiGet<EquipmentType[]>('/equipment-types') })
  const types = typesQ.data ?? []
  const unitCodes = [...new Set(types.map((t) => t.unit_type_code))].sort()
  const subsFor = (code: string) => types.filter((t) => t.unit_type_code === code && t.sub_type).map((t) => t.sub_type as string)
  const rowFor = (code: string, sub: string) =>
    types.find((t) => t.unit_type_code === code && (sub ? t.sub_type === sub : true)) ?? types.find((t) => t.unit_type_code === code)

  const [type, setType] = useState('Padmount Transformer')
  const [sub, setSub] = useState('')
  const [qty, setQty] = useState(12)

  const subs = subsFor(type)
  const effectiveSub = sub || subs[0] || ''
  const size = parseSize(effectiveSub) ?? 1
  const typeRow = rowFor(type, effectiveSub)
  const denominator = typeRow?.natural_denominator ?? '$/unit'

  const priceM = useMutation({ mutationFn: (req: RomPriceRequest) => apiPost<RomBand>('/rom/price', req) })
  const band = priceM.data
  const price = () => priceM.mutate({ type_query: type, denominator, size, qty: Number(qty) })

  const saveM = useMutation({
    mutationFn: () =>
      apiPost<DemandLineRow>('/demand-lines', {
        project_id: PROJECT, qty: Number(qty), equipment_type_id: typeRow?.id ?? null,
        spec_attributes: { type_query: type, denominator, size, sub: effectiveSub },
        rom_unit_price: band?.unit_mid ?? null, rom_confidence: band?.confidence_tier ?? null,
        rom_comparables_count: band?.comparables_count ?? null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['demand-lines'] }),
  })

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', color: '#1a1a1a', maxWidth: 960, margin: '0 auto', padding: '2.5rem 1.5rem' }}>
      <h1 style={{ marginBottom: 2 }}>Viasel — Design &amp; Sourcing</h1>
      <p style={{ color: '#6b7280', marginTop: 0 }}>Price from history → save as demand → freeze → source & award.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginTop: 14 }}>
        <div style={card}>
          <h3 style={{ marginTop: 0, fontSize: 13, textTransform: 'uppercase', letterSpacing: '.06em', color: '#6b7280' }}>Requirement</h3>
          <div style={label}>Equipment type</div>
          <select style={field} value={type} onChange={(e) => { setType(e.target.value); setSub('') }} disabled={typesQ.isLoading}>
            {typesQ.isLoading && <option>loading…</option>}
            {unitCodes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <div style={label}>Size / configuration</div>
          <select style={field} value={effectiveSub} onChange={(e) => setSub(e.target.value)} disabled={subs.length === 0}>
            {subs.length === 0 && <option value="">— none on record —</option>}
            {subs.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <div style={label}>Quantity</div>
          <input style={field} type="number" value={qty} onChange={(e) => setQty(Number(e.target.value))} />
          <div style={{ marginTop: 12, fontSize: 12, color: '#6b7280', display: 'flex', gap: 14 }}>
            <span>size <strong style={chip}>{size}</strong></span>
            <span>denominator <strong style={chip}>{denominator}</strong></span>
          </div>
          <div style={{ fontSize: 11, color: '#9aa0a6', marginTop: 4 }}>size &amp; denominator come from the equipment — not typed</div>
          <button onClick={price} disabled={priceM.isPending} style={{ marginTop: 16, width: '100%', padding: '10px', background: '#2f6f4f', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}>
            {priceM.isPending ? 'Pricing…' : 'Price it'}
          </button>
        </div>

        <div style={card}>
          <h3 style={{ marginTop: 0, fontSize: 13, textTransform: 'uppercase', letterSpacing: '.06em', color: '#6b7280' }}>Price band</h3>
          {priceM.isError && <p style={{ color: '#b23a3a' }}>Couldn’t reach the API (backend on :8000?).</p>}
          {!band && !priceM.isError && <p style={{ color: '#6b7280' }}>Pick a type and hit “Price it”.</p>}
          {band && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontVariantNumeric: 'tabular-nums' }}>
                <span>{money(band.unit_low)}</span><strong style={{ fontSize: 22 }}>{money(band.unit_mid)}</strong><span>{money(band.unit_high)}</span>
              </div>
              <div style={{ height: 10, borderRadius: 6, background: 'linear-gradient(90deg,#e7efe9,#bcd8c6,#e7efe9)', border: '1px solid #c9ccd1', margin: '6px 0' }} />
              <div style={{ fontSize: 12, color: '#6b7280' }}>per unit ({band.denominator}) · extended <strong>{money(band.extended_mid)}</strong> (×{band.qty})</div>
              <div style={{ marginTop: 12, fontSize: 13 }}>Confidence: <strong style={{ color: TIER_COLOR[band.confidence_tier] }}>{band.confidence_tier}</strong> · {band.comparables_count} comparables</div>
              {band.note && <p style={{ fontSize: 12.5, color: '#b7791f', marginTop: 10 }}>{band.note}</p>}
              <button onClick={() => saveM.mutate()} disabled={saveM.isPending || band.unit_mid == null} style={{ marginTop: 14, width: '100%', padding: '9px', background: '#fff', color: '#1a1a1a', border: '1px solid #2f6f4f', borderRadius: 8, fontSize: 13, cursor: 'pointer' }}>
                {saveM.isPending ? 'Saving…' : 'Save as demand line ▸'}
              </button>
            </>
          )}
        </div>
      </div>

      <DemandBoard />
    </main>
  )
}

function DemandBoard() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string[]>([])
  const [scope, setScope] = useState('project')
  const [expanded, setExpanded] = useState<string | null>(null)

  const q = useQuery({ queryKey: ['demand-lines', PROJECT], queryFn: () => apiGet<DemandLineRow[]>(`/demand-lines?project=${PROJECT}`) })
  const lines = q.data ?? []

  const freezeM = useMutation({
    mutationFn: () => apiPost('/freeze', { line_ids: selected, project_id: PROJECT, scope, actor: 'web' }),
    onSuccess: () => { setSelected([]); qc.invalidateQueries({ queryKey: ['demand-lines'] }) },
  })
  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  const describe = (d: DemandLineRow) => {
    const a = d.spec_attributes ?? {}
    return `${String(a.type_query ?? '')} ${String(a.size ?? '')}${String(a.denominator ?? '').replace('$/', ' ')}`.trim()
  }

  return (
    <div style={{ ...card, marginTop: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: 13, textTransform: 'uppercase', letterSpacing: '.06em', color: '#6b7280' }}>Demand board — {PROJECT}</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select value={scope} onChange={(e) => setScope(e.target.value)} style={{ ...field, width: 'auto', padding: '5px 8px' }}>
            <option value="project">project</option><option value="building">building</option><option value="system">system</option>
          </select>
          <button onClick={() => freezeM.mutate()} disabled={selected.length === 0 || freezeM.isPending} style={{ padding: '6px 14px', background: selected.length ? '#2f6f4f' : '#c9ccd1', color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, cursor: selected.length ? 'pointer' : 'default' }}>
            Freeze selected ({selected.length})
          </button>
        </div>
      </div>

      {lines.length === 0 && <p style={{ color: '#6b7280', fontSize: 13 }}>No demand yet — price a requirement above and save it.</p>}
      {lines.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginTop: 8 }}>
          <thead>
            <tr style={{ color: '#6b7280', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              <th style={{ textAlign: 'left', padding: '6px 6px', width: 28 }}></th>
              <th style={{ textAlign: 'left', padding: '6px 6px' }}>Requirement</th>
              <th style={{ textAlign: 'right', padding: '6px 6px' }}>Qty</th>
              <th style={{ textAlign: 'right', padding: '6px 6px' }}>ROM / unit</th>
              <th style={{ textAlign: 'left', padding: '6px 6px' }}>Status</th>
              <th style={{ textAlign: 'right', padding: '6px 6px' }}></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((d) => (
              <Fragment key={d.id}>
                <tr style={{ borderTop: '1px solid #eef0f3' }}>
                  <td style={{ padding: '7px 6px' }}>
                    {d.state === 'drafted' && <input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggle(d.id)} />}
                  </td>
                  <td style={{ padding: '7px 6px' }}>{describe(d) || '—'}</td>
                  <td style={{ padding: '7px 6px', textAlign: 'right' }}>{d.qty}</td>
                  <td style={{ padding: '7px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{money(d.rom_unit_price)}</td>
                  <td style={{ padding: '7px 6px' }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#fff', background: STATE_COLOR[d.state] ?? '#6b7280', borderRadius: 999, padding: '2px 8px' }}>{d.state}</span>
                  </td>
                  <td style={{ padding: '7px 6px', textAlign: 'right' }}>
                    {(d.state === 'frozen' || d.state === 'matched') && (
                      <button onClick={() => setExpanded(expanded === d.id ? null : d.id)} style={{ border: '1px solid #c9ccd1', background: '#fff', borderRadius: 6, padding: '3px 10px', fontSize: 12, cursor: 'pointer' }}>
                        {expanded === d.id ? 'Hide' : 'Source ▸'}
                      </button>
                    )}
                  </td>
                </tr>
                {expanded === d.id && (
                  <tr>
                    <td colSpan={6} style={{ background: '#fafbfc', padding: '12px 10px', borderTop: '1px solid #eef0f3' }}>
                      <SourcingPanel demandLineId={d.id} state={d.state} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function SourcingPanel({ demandLineId, state }: { demandLineId: string; state: string }) {
  const qc = useQueryClient()
  const [vendor, setVendor] = useState('')
  const [unit, setUnit] = useState<number | ''>('')
  const [lead, setLead] = useState<number | ''>('')

  const quotesQ = useQuery({ queryKey: ['quotes', demandLineId], queryFn: () => apiGet<Quote[]>(`/demand-lines/${demandLineId}/quotes`) })
  const quotes = quotesQ.data ?? []
  const awarded = state === 'matched'

  const addM = useMutation({
    mutationFn: () => apiPost(`/demand-lines/${demandLineId}/quotes`, { vendor, unit_price: Number(unit), lead_time_weeks: lead === '' ? null : Number(lead) }),
    onSuccess: () => { setVendor(''); setUnit(''); setLead(''); qc.invalidateQueries({ queryKey: ['quotes', demandLineId] }) },
  })
  const awardM = useMutation({
    mutationFn: (quoteId: string) => apiPost(`/demand-lines/${demandLineId}/award`, { quote_id: quoteId }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['quotes', demandLineId] }); qc.invalidateQueries({ queryKey: ['demand-lines'] }) },
  })

  return (
    <div>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: '#6b7280', marginBottom: 6 }}>
        Sourcing {awarded && '· awarded'}
      </div>

      {!awarded && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <input style={{ ...smallInput, width: 140 }} placeholder="Vendor" value={vendor} onChange={(e) => setVendor(e.target.value)} />
          <input style={{ ...smallInput, width: 120 }} type="number" placeholder="Unit price" value={unit} onChange={(e) => setUnit(e.target.value === '' ? '' : Number(e.target.value))} />
          <input style={{ ...smallInput, width: 100 }} type="number" placeholder="Lead (wk)" value={lead} onChange={(e) => setLead(e.target.value === '' ? '' : Number(e.target.value))} />
          <button onClick={() => addM.mutate()} disabled={!vendor || unit === '' || addM.isPending} style={{ padding: '6px 12px', background: '#1a1a1a', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12.5, cursor: 'pointer' }}>Add quote</button>
        </div>
      )}

      {quotes.length === 0 && <div style={{ color: '#6b7280', fontSize: 12.5 }}>No quotes yet.</div>}
      {quotes.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
          <thead>
            <tr style={{ color: '#6b7280', fontSize: 11 }}>
              <th style={{ textAlign: 'left', padding: '4px 6px' }}>Vendor</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}>Unit price</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}>Lead (wk)</th>
              <th style={{ textAlign: 'right', padding: '4px 6px' }}></th>
            </tr>
          </thead>
          <tbody>
            {quotes.map((qt, i) => (
              <tr key={qt.id} style={{ borderTop: '1px solid #eef0f3', background: qt.state === 'selected' ? '#eef7f0' : 'transparent' }}>
                <td style={{ padding: '5px 6px' }}>{qt.vendor}{i === 0 && !awarded && <span style={{ color: '#2f6f4f', fontSize: 11 }}> · lowest</span>}{qt.state === 'selected' && <span style={{ color: '#2f6f4f', fontSize: 11 }}> · awarded</span>}</td>
                <td style={{ padding: '5px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{money(qt.unit_price)}</td>
                <td style={{ padding: '5px 6px', textAlign: 'right' }}>{qt.lead_time_weeks ?? '—'}</td>
                <td style={{ padding: '5px 6px', textAlign: 'right' }}>
                  {!awarded && <button onClick={() => awardM.mutate(qt.id)} disabled={awardM.isPending} style={{ border: '1px solid #2f6f4f', background: '#fff', color: '#2f6f4f', borderRadius: 6, padding: '2px 10px', fontSize: 12, cursor: 'pointer' }}>Award</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default App

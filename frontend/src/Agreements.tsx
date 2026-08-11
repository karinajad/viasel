import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPost } from './services/api'
import { count, money } from './lib/format'
import { EXHIBIT_KINDS, GATES } from './types/agreement'
import type {
  Agreement, CommittedLine, ExhibitItem, ExhibitKind, ExhibitSet,
  LineCoverage as LineCoverageT, Reconciliation, TypeOption,
} from './types/agreement'
import type { PackageRead } from './types/sourcing'

const STATE_COLOR: Record<string, string> = {
  drafted: '#6b7280', released: '#b7791f', withdrawn: '#9aa0a6',
}

/**
 * Agreements — and the exhibits generated from them.
 *
 * An exhibit is a view of the record, never a file attached to it. That's the mechanism:
 * a placeholder can't survive execution because there's nothing to leave blank, and the
 * executed document can later be reconciled field-by-field against what was generated.
 */
export default function AgreementsFace({ project }: { project: string }) {
  const qc = useQueryClient()
  const agQ = useQuery({
    queryKey: ['agreements', project],
    queryFn: () => apiGet<Agreement[]>(`/agreements?project=${encodeURIComponent(project)}`),
  })
  const pkgQ = useQuery({
    queryKey: ['packages', project],
    queryFn: () => apiGet<PackageRead[]>(`/packages?project=${encodeURIComponent(project)}`),
  })
  const [open, setOpen] = useState<string | null>(null)
  const [picked, setPicked] = useState<string[]>([])

  const agreements = agQ.data ?? []
  // a lot already on an instrument isn't waiting for one; the backend refuses it either way
  const committed = new Set(agreements.flatMap((a) => a.package_ids))
  const awarded = (pkgQ.data ?? []).filter((p) => p.state === 'awarded' && !committed.has(p.id))

  const createM = useMutation({
    mutationFn: () => apiPost<Agreement>('/agreements', { project_id: project, package_ids: picked }),
    onSuccess: (ag) => {
      setPicked([])
      setOpen(ag.id)
      qc.invalidateQueries({ queryKey: ['agreements', project] })
    },
  })

  return (
    <div>
      <div className="headline"><h2>Agreements — {project}</h2><span className="pill live">LIVE · Supabase</span></div>
      <p className="desc">
        The instrument that commits an awarded lot. Contract value is <strong>derived</strong> from the scope
        lines, never stored, so the document and the record can't hold two different totals — and the
        exhibits are generated from that same record rather than typed into a template.
      </p>

      <div className="card">
        <h4 style={{ margin: 0 }}>① Awarded lots waiting for an instrument</h4>
        {awarded.length === 0 && (
          <p style={{ color: 'var(--mut)', fontSize: 13, marginTop: 8 }}>
            Nothing awarded and uncommitted. Award a lot on the <strong>Sourcing</strong> tab.
          </p>
        )}
        {awarded.length > 0 && (
          <>
            <table style={{ marginTop: 8 }}>
              <thead><tr><th style={{ width: 26 }} /><th>Lot</th><th>Equipment</th><th className="num">Units</th><th>Awarded to</th><th className="num">Committed</th></tr></thead>
              <tbody>
                {awarded.map((p) => (
                  <tr key={p.id}>
                    <td><input type="checkbox" checked={picked.includes(p.id)} onChange={() => setPicked((s) => s.includes(p.id) ? s.filter((x) => x !== p.id) : [...s, p.id])} /></td>
                    <td><strong>{p.code}</strong></td>
                    <td>{p.type_query} {p.size}{p.denominator.replace('$/', ' ')}</td>
                    <td className="num">{p.total_qty}</td>
                    <td>{p.awarded_vendor ?? '—'}</td>
                    <td className="num">{money(p.awarded_extended)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
              <button className="btn pri sm" onClick={() => createM.mutate()} disabled={picked.length === 0 || createM.isPending}>
                {createM.isPending ? 'Raising…' : `Raise an agreement over ${count(picked.length, 'lot')} ▸`}
              </button>
              <span style={{ fontSize: 11, color: 'var(--mut)' }}>
                One instrument, one counterparty — lots awarded to different vendors can't share an agreement.
              </span>
              {createM.isError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{String(createM.error).replace(/^Error:\s*/, '')}</span>}
            </div>
          </>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h4 style={{ margin: 0 }}>② Agreements</h4>
        {agreements.length === 0 && <p style={{ color: 'var(--mut)', fontSize: 13, marginTop: 8 }}>None yet.</p>}
        {agreements.length > 0 && (
          <table style={{ marginTop: 8 }}>
            <thead><tr><th>PO number</th><th>Vendor</th><th className="num">Lines</th><th className="num">Units</th><th className="num">Contract value</th><th>State</th><th>Released</th><th /></tr></thead>
            <tbody>
              {agreements.map((a) => (
                <Fragment key={a.id}>
                  <tr>
                    <td>
                      <strong>{a.code}</strong>
                      <div style={{ fontSize: 10.5, color: 'var(--mut)' }}>{a.package_codes.join(' · ')}</div>
                    </td>
                    <td>{a.vendor_name}</td>
                    <td className="num">{a.line_count}</td>
                    <td className="num">{a.total_qty}</td>
                    <td className="num"><strong>{money(a.contract_value)}</strong></td>
                    <td><span className="st" style={{ background: STATE_COLOR[a.state] ?? '#6b7280' }}>{a.state}</span></td>
                    <td style={{ color: a.released_date ? 'var(--ink)' : 'var(--line)' }}>{a.released_date ?? '—'}</td>
                    <td className="num"><button className="btn sm" onClick={() => setOpen(open === a.id ? null : a.id)}>{open === a.id ? 'Hide' : 'Exhibits ▸'}</button></td>
                  </tr>
                  {open === a.id && <tr><td colSpan={8} style={{ background: '#fafbfc' }}><Exhibits agreementId={a.id} project={project} /></td></tr>}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function Exhibits({ agreementId, project }: { agreementId: string; project: string }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['exhibits', agreementId], queryFn: () => apiGet<ExhibitSet>(`/agreements/${agreementId}/exhibits`) })
  const rec = useQuery({ queryKey: ['reconciliation', agreementId], queryFn: () => apiGet<Reconciliation | null>(`/agreements/${agreementId}/reconciliation`) })
  const [copied, setCopied] = useState(false)
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['exhibits', agreementId] })
    qc.invalidateQueries({ queryKey: ['reconciliation', agreementId] })
    qc.invalidateQueries({ queryKey: ['agreements', project] })
  }
  const releaseM = useMutation({
    mutationFn: () => apiPost(`/agreements/${agreementId}/release`, { released_date: new Date().toISOString().slice(0, 10) }),
    onSuccess: refresh,
  })
  const addM = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiPost(`/agreements/${agreementId}/exhibit-items`, payload),
    onSuccess: refresh,
  })
  const dropM = useMutation({
    mutationFn: (id: string) => apiDelete(`/agreements/${agreementId}/exhibit-items/${id}`),
    onSuccess: refresh,
  })

  if (q.isLoading || !q.data) return <div style={{ padding: 8, color: 'var(--mut)', fontSize: 12.5 }}>Loading…</div>
  const { agreement: a, cover_sheet: c, equipment_list: rows, legend, items, delivery_coverage, committed_lines, equipment_types, roj_dates } = q.data
  const listTotal = rows.reduce((n, r) => n + r.extended_price, 0)

  const copyEquipmentList = () => {
    const head = ['Design term', 'Spec', 'Building', 'Area', 'Qty', 'Unit price', 'Extended', 'Lead (wks)', 'OEM']
    const tsv = [head, ...rows.map((r) => [
      r.design_term ?? '', r.equipment_spec ?? '', r.building ?? '', r.area ?? '',
      r.qty, r.unit_price, r.extended_price, r.lead_time_weeks ?? '', r.oem ?? '',
    ])].map((line) => line.join('\t')).join('\n')
    void navigator.clipboard.writeText(tsv).then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="printable" style={{ padding: '8px 2px' }}>
      <div className="no-print" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        {a.state === 'drafted' && (
          <>
            <button className="btn sm" onClick={() => releaseM.mutate()} disabled={releaseM.isPending}>Release for signature ▸</button>
            <span style={{ fontSize: 11, color: 'var(--mut)' }}>
              Hands the exhibit data over. Signing happens in whichever system you already execute in.
            </span>
          </>
        )}
        {a.state === 'released' && !rec.data && <RegisterExecuted agreementId={agreementId} onDone={refresh} />}
        {rec.data && <Reconciled rec={rec.data} />}
        {releaseM.isError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{String(releaseM.error).replace(/^Error:\s*/, '')}</span>}
      </div>

      <Sub>Cover sheet</Sub>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: 12.5, marginBottom: 14 }}>
        <div>
          <div style={{ color: 'var(--mut)', fontSize: 11 }}>BUYER</div>
          <div><strong>{c.buyer_entity ?? '— no buyer entity on the project —'}</strong></div>
          <div style={{ color: 'var(--mut)' }}>{c.project_address ?? '—'}</div>
          <div style={{ color: 'var(--mut)' }}>{c.project_name}{c.site_code ? ` · ${c.site_code}` : ''}</div>
        </div>
        <div>
          <div style={{ color: 'var(--mut)', fontSize: 11 }}>SELLER</div>
          <div><strong>{c.vendor_name}</strong>{c.vendor_code ? ` · ${c.vendor_code}` : ''}</div>
          {c.vendor_contacts.length === 0
            ? <div style={{ color: 'var(--mut)' }}>no contacts on the vendor record</div>
            : c.vendor_contacts.map((x) => <div key={x} style={{ color: 'var(--mut)' }}>{x}</div>)}
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--mut)', marginBottom: 14 }}>
        PO <strong style={{ color: 'var(--ink)' }}>{c.po_number}</strong> · released {c.date_of_issue ?? '—'}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <Sub>Exhibit A — equipment list</Sub>
        <div className="no-print" style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
          <button className="btn sm" onClick={copyEquipmentList}>{copied ? '✓ copied' : 'Copy for Excel'}</button>
          <button className="btn sm" onClick={() => window.print()}>Print</button>
        </div>
      </div>
      <table style={{ marginBottom: 14 }}>
        <thead><tr><th>Design term</th><th>Spec</th><th>Where</th><th className="num">Qty</th><th className="num">Unit price</th><th className="num">Extended</th><th className="num">Lead</th><th>OEM</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td><strong>{r.design_term ?? '—'}</strong></td>
              <td>{r.equipment_spec ?? '—'}</td>
              <td>{r.building ?? 'unassigned'}{r.area ? ` · ${r.area}` : ''}</td>
              <td className="num">{r.qty}</td>
              <td className="num">{money(r.unit_price)}</td>
              <td className="num">{money(r.extended_price)}</td>
              <td className="num">{r.lead_time_weeks ?? '—'}</td>
              <td style={{ color: 'var(--mut)' }}>{r.oem ?? '—'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3} style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)' }}>Total</td>
            <td className="num"><strong>{a.total_qty}</strong></td>
            <td />
            <td className="num"><strong>{money(listTotal)}</strong></td>
            <td colSpan={2} style={{ fontSize: 11, color: Math.abs(listTotal - a.contract_value) < 0.01 ? 'var(--accent)' : 'var(--red)' }}>
              {Math.abs(listTotal - a.contract_value) < 0.01 ? '= contract value, by construction' : 'does not match the contract value'}
            </td>
          </tr>
        </tfoot>
      </table>

      <Coverage coverage={delivery_coverage} />

      {EXHIBIT_KINDS.map((kind) => (
        <ExhibitTab
          key={kind}
          kind={kind}
          items={items[kind] ?? []}
          lines={committed_lines}
          types={equipment_types}
          rojDates={roj_dates}
          onAdd={(payload) => addM.mutate(payload)}
          onDrop={(id) => dropM.mutate(id)}
          pending={addM.isPending}
          error={addM.isError ? String(addM.error).replace(/^Error:\s*/, '') : null}
        />
      ))}

      <Sub>Exhibit — legend</Sub>
      {legend.length === 0
        ? <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No codes on the project yet.</div>
        : <table>
            <tbody>
              {legend.map((l) => (
                <tr key={`${l.kind}-${l.code}`}>
                  <td style={{ color: 'var(--mut)', width: 90 }}>{l.kind}</td>
                  <td><strong>{l.code}</strong></td>
                  <td style={{ color: 'var(--mut)' }}>{l.description ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>}
    </div>
  )
}

/** How much of each committed line the delivery schedule accounts for. */
function Coverage({ coverage }: { coverage: LineCoverageT[] }) {
  if (coverage.length === 0) return null
  const short = coverage.filter((c) => c.remaining_qty > 0)
  return (
    <div style={{ marginBottom: 14 }}>
      <Sub>Delivery coverage · what the schedule accounts for</Sub>
      <table>
        <tbody>
          {coverage.map((c) => (
            <tr key={c.scope_line_id}>
              <td>{c.label}</td>
              <td className="num" style={{ width: 130 }}>
                <strong>{c.scheduled_qty}</strong> / {c.committed_qty}
              </td>
              <td style={{ width: 170, color: c.remaining_qty === 0 ? 'var(--accent)' : 'var(--amber)', fontSize: 12 }}>
                {c.remaining_qty === 0 ? 'fully scheduled' : `${c.remaining_qty} unscheduled`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {short.length > 0 && (
        <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 4 }}>
          A schedule can never promise more units than were bought — that cap is what ties this exhibit
          back to the demand assigned at sourcing.
        </div>
      )}
    </div>
  )
}

/** What each tab is for, and which fields it needs. The differences are the point. */
const TABS: Record<ExhibitKind, {
  title: string
  hint: string
  needsLine: boolean | 'optional'
  needsType?: boolean
  needsPlace?: boolean
  needsQty?: boolean
  needsPrice?: boolean
  needsDate?: 'free' | 'roj'
  needsGate?: boolean
  typeToggle?: boolean
}> = {
  delivery_schedule: {
    title: 'Exhibit B — delivery schedule (ROJ)',
    hint: 'Tranches against the units bought. It can never promise more than was committed.',
    needsLine: 'optional', needsQty: true, needsDate: 'free',
  },
  spare_parts: {
    title: 'Exhibit — spare parts',
    hint: 'Spares carried with a specific committed line — the units allocated to this vendor.',
    needsLine: true, needsQty: true, needsPrice: true,
  },
  bill_of_materials: {
    title: 'Exhibit — bill of materials',
    hint: "What's inside a committed line.",
    needsLine: true, needsQty: true,
  },
  shipping_capacity: {
    title: 'Exhibit — shipping capacity',
    hint: 'Throughput per equipment type, per place, from a date already confirmed on the schedule.',
    needsLine: false, needsType: true, needsPlace: true, needsQty: true, needsDate: 'roj',
  },
  required_documents: {
    title: 'Exhibit — required documents',
    hint: 'Owed at a gate. Attach to an equipment type, not to every unit of it.',
    needsLine: 'optional', needsGate: true, typeToggle: true,
  },
}

function ExhibitTab({ kind, items, lines, types, rojDates, onAdd, onDrop, pending, error }: {
  kind: ExhibitKind
  items: ExhibitItem[]
  lines: CommittedLine[]
  types: TypeOption[]
  rojDates: string[]
  onAdd: (payload: Record<string, unknown>) => void
  onDrop: (id: string) => void
  pending: boolean
  error: string | null
}) {
  const spec = TABS[kind]
  const [desc, setDesc] = useState('')
  const [lineId, setLineId] = useState('')
  const [typeId, setTypeId] = useState('')
  const [grain, setGrain] = useState<'type' | 'line' | 'all'>('type')
  const [place, setPlace] = useState('')
  const [qty, setQty] = useState<number | ''>('')
  const [price, setPrice] = useState<number | ''>('')
  const [date, setDate] = useState('')
  const [gate, setGate] = useState(GATES[0])

  const places = [...new Map(lines.map((l) => [`${l.building}|${l.area ?? ''}`, l])).values()]
  const submit = () => {
    const payload: Record<string, unknown> = { exhibit: kind, description: desc }
    if (spec.typeToggle) {
      if (grain === 'type') payload.equipment_type_id = typeId || null
      if (grain === 'line') payload.scope_line_id = lineId || null
    } else {
      if (spec.needsLine !== false && lineId) payload.scope_line_id = lineId
      if (spec.needsType) payload.equipment_type_id = typeId || null
    }
    if (spec.needsPlace && place) {
      const [b, a] = place.split('|')
      payload.building = b
      payload.area = a || null
    }
    if (spec.needsQty) payload.qty = qty === '' ? null : Number(qty)
    if (spec.needsPrice) payload.unit_price = price === '' ? null : Number(price)
    if (spec.needsDate) payload.due_date = date || null
    if (spec.needsGate) payload.gate = gate
    onAdd(payload)
    setDesc(''); setQty(''); setPrice('')
  }

  const lineLabel = (id: string | null) => lines.find((l) => l.scope_line_id === id)?.label
  const typeLabel = (id: string | null) => types.find((o) => o.equipment_type_id === id)?.label

  return (
    <div style={{ marginBottom: 16 }}>
      <Sub>{spec.title}</Sub>
      <div className="no-print" style={{ fontSize: 11, color: '#9aa0a6', marginTop: -3, marginBottom: 6 }}>{spec.hint}</div>

      <div className="no-print" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 8 }}>
        {spec.typeToggle && (
          <div style={{ width: 128 }}>
            <label style={{ margin: '0 0 3px' }}>Attach to</label>
            <select className="si" style={{ width: '100%' }} value={grain} onChange={(e) => setGrain(e.target.value as 'type' | 'line' | 'all')}>
              <option value="type">equipment type</option>
              <option value="line">one line</option>
              <option value="all">whole agreement</option>
            </select>
          </div>
        )}
        {((spec.typeToggle && grain === 'type') || spec.needsType) && (
          <div style={{ width: 210 }}>
            <label style={{ margin: '0 0 3px' }}>Equipment type</label>
            <select className="si" style={{ width: '100%' }} value={typeId} onChange={(e) => setTypeId(e.target.value)}>
              <option value="">— pick —</option>
              {types.filter((o) => o.equipment_type_id).map((o) => (
                <option key={o.equipment_type_id} value={o.equipment_type_id ?? ''}>{o.label} ({o.unit_count})</option>
              ))}
            </select>
          </div>
        )}
        {((spec.typeToggle && grain === 'line') || (!spec.typeToggle && spec.needsLine !== false)) && (
          <div style={{ width: 250 }}>
            <label style={{ margin: '0 0 3px' }}>
              Committed line{spec.needsLine === true && <span style={{ color: 'var(--red)' }}> *</span>}
            </label>
            <select className="si" style={{ width: '100%' }} value={lineId} onChange={(e) => setLineId(e.target.value)}>
              <option value="">{spec.needsLine === 'optional' ? '— whole agreement —' : '— pick a line —'}</option>
              {lines.map((l) => <option key={l.scope_line_id} value={l.scope_line_id}>{l.label} (×{l.qty})</option>)}
            </select>
          </div>
        )}
        {spec.needsPlace && (
          <div style={{ width: 150 }}>
            <label style={{ margin: '0 0 3px' }}>Building / area <span style={{ color: 'var(--red)' }}>*</span></label>
            <select className="si" style={{ width: '100%' }} value={place} onChange={(e) => setPlace(e.target.value)}>
              <option value="">— pick —</option>
              {places.map((l) => (
                <option key={`${l.building}|${l.area ?? ''}`} value={`${l.building}|${l.area ?? ''}`}>
                  {l.building}{l.area ? ` · ${l.area}` : ''}
                </option>
              ))}
            </select>
          </div>
        )}
        <div style={{ width: 200 }}>
          <label style={{ margin: '0 0 3px' }}>Description <span style={{ color: 'var(--red)' }}>*</span></label>
          <input className="si" style={{ width: '100%' }} value={desc} onChange={(e) => setDesc(e.target.value)} />
        </div>
        {spec.needsQty && (
          <div style={{ width: 74 }}>
            <label style={{ margin: '0 0 3px' }}>Qty</label>
            <input className="si" style={{ width: '100%' }} type="number" min={1} value={qty} onChange={(e) => setQty(e.target.value === '' ? '' : Number(e.target.value))} />
          </div>
        )}
        {spec.needsPrice && (
          <div style={{ width: 110 }}>
            <label style={{ margin: '0 0 3px' }}>$ / unit</label>
            <input className="si" style={{ width: '100%' }} type="number" value={price} onChange={(e) => setPrice(e.target.value === '' ? '' : Number(e.target.value))} />
          </div>
        )}
        {spec.needsDate === 'free' && (
          <div style={{ width: 140 }}>
            <label style={{ margin: '0 0 3px' }}>ROJ date <span style={{ color: 'var(--red)' }}>*</span></label>
            <input className="si" style={{ width: '100%' }} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
        )}
        {spec.needsDate === 'roj' && (
          <div style={{ width: 150 }}>
            <label style={{ margin: '0 0 3px' }}>From (confirmed ROJ) <span style={{ color: 'var(--red)' }}>*</span></label>
            <select className="si" style={{ width: '100%' }} value={date} onChange={(e) => setDate(e.target.value)} disabled={rojDates.length === 0}>
              <option value="">{rojDates.length === 0 ? '— none confirmed yet —' : '— pick —'}</option>
              {rojDates.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        )}
        {spec.needsGate && (
          <div style={{ width: 210 }}>
            <label style={{ margin: '0 0 3px' }}>Owed at <span style={{ color: 'var(--red)' }}>*</span></label>
            <select className="si" style={{ width: '100%' }} value={gate} onChange={(e) => setGate(e.target.value)}>
              {GATES.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
        )}
        <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }}
          onClick={submit} disabled={!desc || pending}>Add</button>
      </div>
      {error && <div className="note no-print" style={{ marginTop: 0 }}>{error}</div>}

      {items.length === 0
        ? <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>Nothing entered yet.</div>
        : <table>
            <tbody>
              {items.map((i) => (
                <tr key={i.id}>
                  <td><strong>{i.description}</strong>{i.note && <span style={{ color: 'var(--mut)' }}> · {i.note}</span>}</td>
                  <td style={{ color: 'var(--mut)', fontSize: 12 }}>
                    {i.equipment_type_id ? typeLabel(i.equipment_type_id)
                      : i.scope_line_id ? lineLabel(i.scope_line_id)
                      : i.building ? `${i.building}${i.area ? ` · ${i.area}` : ''}` : 'whole agreement'}
                  </td>
                  <td className="num" style={{ width: 60 }}>{i.qty ?? ''}</td>
                  <td className="num" style={{ width: 100 }}>{i.unit_price != null ? money(i.unit_price) : ''}</td>
                  <td style={{ width: 110, color: 'var(--mut)', fontSize: 12 }}>{i.due_date ?? ''}</td>
                  <td style={{ width: 180, color: 'var(--amber)', fontSize: 11.5 }}>{i.gate ?? ''}</td>
                  <td className="num no-print" style={{ width: 40 }}>
                    <button className="btn sm danger" onClick={() => onDrop(i.id)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>}
    </div>
  )
}

/** Register the signed version — where it lives, and what it says. */
function RegisterExecuted({ agreementId, onDone }: { agreementId: string; onDone: () => void }) {
  const [open, setOpen] = useState(false)
  const [f, setF] = useState<Record<string, string>>({ source_system: 'Procore' })
  const set = (k: string, v: string) => setF((d) => ({ ...d, [k]: v }))
  const m = useMutation({
    mutationFn: () => apiPost(`/agreements/${agreementId}/executed`, {
      source_system: f.source_system,
      external_document_ref: f.external_document_ref || null,
      execution_date: f.execution_date || null,
      stated_po_number: f.stated_po_number || null,
      stated_buyer_entity: f.stated_buyer_entity || null,
      stated_vendor_name: f.stated_vendor_name || null,
      stated_total_qty: f.stated_total_qty ? Number(f.stated_total_qty) : null,
      stated_contract_value: f.stated_contract_value ? Number(f.stated_contract_value) : null,
      retrieved_by: 'web',
    }),
    onSuccess: () => { setOpen(false); onDone() },
  })

  if (!open) return (
    <>
      <button className="btn sm" onClick={() => setOpen(true)}>Register the signed version ▸</button>
      <span style={{ fontSize: 11, color: 'var(--mut)' }}>
        Viasel holds the executed document and reconciles it — it doesn't own the instrument.
      </span>
    </>
  )
  const fld = (k: string, label: string, type = 'text', w = 150) => (
    <div style={{ width: w }}>
      <label style={{ margin: '0 0 3px' }}>{label}</label>
      <input className="si" style={{ width: '100%' }} type={type} value={f[k] ?? ''} onChange={(e) => set(k, e.target.value)} />
    </div>
  )
  return (
    <div style={{ width: '100%' }}>
      <div style={{ fontSize: 11, color: 'var(--mut)', marginBottom: 6 }}>
        As read off the signed document. Leave a field blank if you didn't read it —
        blank means "not stated", which is different from "disagrees".
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        {fld('source_system', 'Held in', 'text', 130)}
        {fld('external_document_ref', 'Their ref', 'text', 140)}
        {fld('execution_date', 'Executed', 'date', 140)}
        {fld('stated_po_number', 'PO number on it', 'text', 140)}
        {fld('stated_vendor_name', 'Vendor on it', 'text', 150)}
        {fld('stated_total_qty', 'Total qty on it', 'number', 110)}
        {fld('stated_contract_value', 'Value on it', 'number', 130)}
        <button className="btn pri sm" onClick={() => m.mutate()} disabled={!f.source_system || m.isPending}>
          {m.isPending ? 'Reconciling…' : 'Register & reconcile'}
        </button>
        <button className="btn sm" onClick={() => setOpen(false)}>Cancel</button>
      </div>
      {m.isError && <div className="note">{String(m.error).replace(/^Error:\s*/, '')}</div>}
    </div>
  )
}

function Reconciled({ rec }: { rec: Reconciliation }) {
  const { executed: e, divergences: d } = rec
  const clean = d.length === 0
  return (
    <div style={{ width: '100%' }}>
      <div style={{ fontSize: 12 }}>
        Executed {e.execution_date ?? '—'} · held in <strong>{e.source_system}</strong>
        {e.external_document_ref && <> as {e.external_document_ref}</>} ·{' '}
        <strong style={{ color: clean ? 'var(--accent)' : 'var(--red)' }}>
          {clean ? 'reconciles' : `${d.length} field${d.length === 1 ? '' : 's'} diverged`}
        </strong>
      </div>
      {!clean && (
        <table style={{ marginTop: 6 }}>
          <thead><tr><th>Field</th><th className="num">Record generated</th><th className="num">Signed document says</th></tr></thead>
          <tbody>
            {d.map((x) => (
              <tr key={x.id}>
                <td>{x.field_name.replace(/_/g, ' ')}</td>
                <td className="num">{x.generated_value ?? '—'}</td>
                <td className="num" style={{ color: 'var(--red)' }}>{x.executed_value ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!clean && (
        <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 4 }}>
          Flagged, never applied. The record still holds what it committed — adopting the document's
          number silently would erase the only evidence the change happened outside it.
        </div>
      )}
    </div>
  )
}

function Sub({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)', marginBottom: 6 }}>{children}</div>
}

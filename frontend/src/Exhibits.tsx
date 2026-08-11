import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPatch, apiPost } from './services/api'
import { count, money } from './lib/format'
import { GATES } from './types/agreement'
import type { ExhibitItem, ExhibitSet, Reconciliation } from './types/agreement'

/**
 * The exhibit set, one exhibit at a time.
 *
 * Each tab mirrors the column shape of the workbook tab it replaces, because the
 * differences between them are the content: a delivery schedule carries the vendor's date
 * beside the site's, a bill of materials asks whether a component is in the price, spares
 * carry their own lead time, and Schedule D hangs a document off a named trigger.
 */
const TABS = [
  ['cover', 'Cover sheet'],
  ['equipment', 'Exhibit A · equipment list'],
  ['delivery', 'Delivery schedule'],
  ['spares', 'Spare parts'],
  ['bom', 'Bill of materials'],
  ['capacity', 'Shipping capacity'],
  ['documents', 'Schedule D · documents'],
  ['legend', 'Legend'],
] as const
type TabKey = (typeof TABS)[number][0]

export default function Exhibits({ agreementId, project }: { agreementId: string; project: string }) {
  const qc = useQueryClient()
  const [tab, setTab] = useState<TabKey>('cover')
  const q = useQuery({ queryKey: ['exhibits', agreementId], queryFn: () => apiGet<ExhibitSet>(`/agreements/${agreementId}/exhibits`) })
  const rec = useQuery({ queryKey: ['reconciliation', agreementId], queryFn: () => apiGet<Reconciliation | null>(`/agreements/${agreementId}/reconciliation`) })

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
  const patchM = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Record<string, unknown> }) =>
      apiPatch(`/agreements/${agreementId}/exhibit-items/${id}`, patch),
    onSuccess: refresh,
  })
  const dropM = useMutation({
    mutationFn: (id: string) => apiDelete(`/agreements/${agreementId}/exhibit-items/${id}`),
    onSuccess: refresh,
  })
  const err = [addM, patchM, dropM].map((m) => (m.isError ? String(m.error) : null)).find(Boolean)

  if (q.isLoading || !q.data) return <div style={{ padding: 8, color: 'var(--mut)', fontSize: 12.5 }}>Loading…</div>
  const ex = q.data
  const ctx = { ex, add: addM.mutate, patch: patchM.mutate, drop: dropM.mutate }
  const counts: Partial<Record<TabKey, number>> = {
    delivery: (ex.items.delivery_schedule ?? []).length,
    spares: (ex.items.spare_parts ?? []).length,
    bom: (ex.items.bill_of_materials ?? []).length,
    capacity: (ex.items.shipping_capacity ?? []).length,
    documents: (ex.items.required_documents ?? []).length,
  }

  return (
    <div style={{ padding: '8px 2px' }}>
      <div className="no-print" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
        {ex.agreement.state === 'drafted' && (
          <>
            <button className="btn sm" onClick={() => releaseM.mutate()} disabled={releaseM.isPending}>Release for signature ▸</button>
            <span style={{ fontSize: 11, color: 'var(--mut)' }}>
              Hands the exhibit data over. Signing happens in whichever system you already execute in.
            </span>
          </>
        )}
        {ex.agreement.state === 'released' && !rec.data && <RegisterExecuted agreementId={agreementId} onDone={refresh} />}
        {rec.data && <Reconciled rec={rec.data} />}
      </div>

      <div className="exhibtabs no-print">
        {TABS.map(([k, label]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
            {label}{counts[k] ? <span className="n">{counts[k]}</span> : null}
          </button>
        ))}
      </div>

      <div className="printable">
        {tab === 'cover' && <Cover ex={ex} />}
        {tab === 'equipment' && <EquipmentList ex={ex} />}
        {tab === 'delivery' && <Delivery {...ctx} />}
        {tab === 'spares' && <Spares {...ctx} />}
        {tab === 'bom' && <Bom {...ctx} />}
        {tab === 'capacity' && <Capacity {...ctx} />}
        {tab === 'documents' && <Documents {...ctx} />}
        {tab === 'legend' && <Legend ex={ex} />}
      </div>
      {err && <div className="note no-print">{err.replace(/^Error:\s*/, '')}</div>}
    </div>
  )
}

interface Ctx {
  ex: ExhibitSet
  add: (payload: Record<string, unknown>) => void
  patch: (v: { id: string; patch: Record<string, unknown> }) => void
  drop: (id: string) => void
}

function Head({ ex, title }: { ex: ExhibitSet; title: string }) {
  const c = ex.cover_sheet
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12.5, fontWeight: 700 }}>{title}</div>
      <div style={{ fontSize: 11, color: 'var(--mut)' }}>
        PO {c.po_number} · {c.vendor_name} · {c.buyer_entity ?? 'no buyer entity'} · {c.project_name}
      </div>
    </div>
  )
}

function Cover({ ex }: { ex: ExhibitSet }) {
  const c = ex.cover_sheet
  return (
    <div>
      <Head ex={ex} title="VENDOR DATA" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: 12.5 }}>
        <div>
          <div style={{ color: 'var(--mut)', fontSize: 11 }}>BUYER</div>
          <div><strong>{c.buyer_entity ?? '— none on the project —'}</strong></div>
          <div style={{ color: 'var(--mut)' }}>{c.project_address ?? '—'}</div>
          <div style={{ color: 'var(--mut)' }}>{c.project_name}{c.site_code ? ` · site ${c.site_code}` : ''}</div>
        </div>
        <div>
          <div style={{ color: 'var(--mut)', fontSize: 11 }}>SELLER</div>
          <div><strong>{c.vendor_name}</strong>{c.vendor_code ? ` · ${c.vendor_code}` : ''}</div>
          {c.vendor_contacts.length === 0
            ? <div style={{ color: 'var(--mut)' }}>no contacts on the vendor record</div>
            : c.vendor_contacts.map((x) => <div key={x} style={{ color: 'var(--mut)' }}>{x}</div>)}
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--mut)', marginTop: 10 }}>
        Date of issue {c.date_of_issue ?? '—'} · {count(ex.agreement.total_qty, 'unit')} ·{' '}
        <strong style={{ color: 'var(--ink)' }}>{money(ex.agreement.contract_value)}</strong> derived from the scope lines
      </div>
    </div>
  )
}

function EquipmentList({ ex }: { ex: ExhibitSet }) {
  const [copied, setCopied] = useState(false)
  const rows = ex.equipment_list
  const total = rows.reduce((n, r) => n + r.extended_price, 0)
  const copy = () => {
    const head = ['Related Design Term', 'Related Equipment Spec', 'Vendor Description', 'Building', 'Area', 'Qty', 'Unit Price', 'Extended Price', 'Lead Time (Weeks)', 'OEM']
    const tsv = [head, ...rows.map((r) => [
      r.design_term ?? '', r.equipment_spec ?? '', r.vendor_description ?? '', r.building ?? '',
      r.area ?? '', r.qty, r.unit_price, r.extended_price, r.lead_time_weeks ?? '', r.oem ?? '',
    ])].map((l) => l.join('\t')).join('\n')
    void navigator.clipboard.writeText(tsv).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 2000) })
  }
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Head ex={ex} title="EQUIPMENT LIST" />
        <div className="no-print" style={{ display: 'flex', gap: 6 }}>
          <button className="btn sm" onClick={copy}>{copied ? '✓ copied' : 'Copy for Excel'}</button>
          <button className="btn sm" onClick={() => window.print()}>Print</button>
        </div>
      </div>
      <table>
        <thead><tr><th>Related Design Term</th><th>Equipment Spec</th><th>Vendor Description</th><th>Building</th><th>Area</th><th className="num">Qty</th><th className="num">Unit Price</th><th className="num">Extended</th><th className="num">Lead</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td><strong>{r.design_term ?? '—'}</strong></td>
              <td>{r.equipment_spec ?? '—'}</td>
              <td style={{ color: 'var(--mut)' }}>{r.vendor_description ?? '—'}</td>
              <td>{r.building ?? '—'}</td>
              <td>{r.area ?? '—'}</td>
              <td className="num">{r.qty}</td>
              <td className="num">{money(r.unit_price)}</td>
              <td className="num">{money(r.extended_price)}</td>
              <td className="num">{r.lead_time_weeks ?? '—'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr>
          <td colSpan={5} style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--mut)' }}>Total</td>
          <td className="num"><strong>{ex.agreement.total_qty}</strong></td>
          <td />
          <td className="num"><strong>{money(total)}</strong></td>
          <td style={{ fontSize: 10.5, color: 'var(--accent)' }}>= contract value</td>
        </tr></tfoot>
      </table>
    </div>
  )
}

/** Delivery schedule — one row per committed line, carrying the vendor's date and the site's. */
function Delivery({ ex, add, patch, drop }: Ctx) {
  const rows = ex.items.delivery_schedule ?? []
  const byLine = (id: string) => rows.filter((r) => r.scope_line_id === id)
  const cover = Object.fromEntries(ex.delivery_coverage.map((c) => [c.scope_line_id, c]))

  return (
    <div>
      <Head ex={ex} title="DELIVERY SCHEDULE" />
      <div className="no-print" style={{ fontSize: 11, color: '#9aa0a6', marginBottom: 8 }}>
        A tranche per line, or several if it lands in stages. The vendor's committed date sits beside
        the ROJ the site needs, and the quantities can never exceed what was bought.
      </div>
      <table>
        <thead><tr>
          <th>Related Design Term</th><th>Spec</th><th>Building</th><th>Area</th>
          <th className="num">Qty</th><th>Vendor Delivery Date</th><th>ROJ Date</th><th>Designation</th><th className="no-print" />
        </tr></thead>
        <tbody>
          {ex.committed_lines.map((l) => {
            const mine = byLine(l.scope_line_id)
            const left = cover[l.scope_line_id]?.remaining_qty ?? l.qty
            return (
              <>
                {mine.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{l.design_term ?? '—'}</strong></td>
                    <td>{l.label.split(' · ')[0].replace(`${l.design_term ?? ''} `, '')}</td>
                    <td>{l.building ?? '—'}</td>
                    <td>{l.area ?? '—'}</td>
                    <td className="num">
                      <input className="si" style={{ width: 56, textAlign: 'right' }} type="number" min={1} defaultValue={r.qty ?? ''}
                        onBlur={(e) => { const v = Number(e.target.value); if (v && v !== r.qty) patch({ id: r.id, patch: { qty: v } }) }} />
                    </td>
                    <td>
                      <input className="si" type="date" defaultValue={r.vendor_delivery_date ?? ''}
                        onBlur={(e) => patch({ id: r.id, patch: { vendor_delivery_date: e.target.value || null } })} />
                    </td>
                    <td>
                      <input className="si" type="date" defaultValue={r.due_date ?? ''}
                        onBlur={(e) => patch({ id: r.id, patch: { due_date: e.target.value || null } })} />
                    </td>
                    <td>
                      <input className="si" style={{ width: 120 }} defaultValue={r.designation ?? ''} placeholder="OFCI to Site"
                        onBlur={(e) => patch({ id: r.id, patch: { designation: e.target.value || null } })} />
                    </td>
                    <td className="num no-print"><button className="btn sm danger" onClick={() => drop(r.id)}>✕</button></td>
                  </tr>
                ))}
                <tr key={`${l.scope_line_id}-add`} className="no-print">
                  <td colSpan={4} style={{ color: 'var(--mut)', fontSize: 12 }}>
                    {mine.length === 0 ? <strong>{l.label}</strong> : <span style={{ paddingLeft: 12 }}>↳ another tranche</span>}
                  </td>
                  <td colSpan={5}>
                    <button className="btn sm" disabled={left <= 0}
                      onClick={() => add({ exhibit: 'delivery_schedule', scope_line_id: l.scope_line_id, description: `${l.design_term ?? 'Equipment'} — ${l.building ?? ''}`.trim(), qty: left, designation: 'OFCI to Site' })}>
                      {left > 0 ? `+ tranche for ${count(left, 'unit')}` : 'fully scheduled'}
                    </button>
                  </td>
                </tr>
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** Spare parts — a parent item picked from the committed lines, then the spares under it. */
function Spares({ ex, add, patch, drop }: Ctx) {
  return (
    <ParentChild
      ex={ex} add={add} patch={patch} drop={drop}
      exhibit="spare_parts" title="SPARE PARTS LIST"
      hint="Each parent is a committed line. Spares carry their own lead time, since a spare you can't get in time isn't a spare."
      childLabel="Spare Part Item"
      extraHead={<><th className="num">LLE Lead (wks)</th><th className="num">$ / unit</th></>}
      extraCells={(r) => (
        <>
          <td className="num">
            <input className="si" style={{ width: 62, textAlign: 'right' }} type="number" defaultValue={r.lead_time_weeks ?? ''}
              onBlur={(e) => patch({ id: r.id, patch: { lead_time_weeks: e.target.value ? Number(e.target.value) : null } })} />
          </td>
          <td className="num">
            <input className="si" style={{ width: 90, textAlign: 'right' }} type="number" defaultValue={r.unit_price ?? ''}
              onBlur={(e) => patch({ id: r.id, patch: { unit_price: e.target.value ? Number(e.target.value) : null } })} />
          </td>
        </>
      )}
    />
  )
}

/** Bill of materials — parent item, then components, each in or out of the price. */
function Bom({ ex, add, patch, drop }: Ctx) {
  return (
    <ParentChild
      ex={ex} add={add} patch={patch} drop={drop}
      exhibit="bill_of_materials" title="EQUIPMENT DETAIL — PARENT / SUB-COMPONENT"
      hint="Only needed where a line has components worth naming. Included? says whether it's in the price already."
      childLabel="Component / Sub-Item"
      extraHead={<th>Included?</th>}
      extraCells={(r) => (
        <td>
          <select className="si" value={r.is_included == null ? '' : r.is_included ? 'y' : 'n'}
            onChange={(e) => patch({ id: r.id, patch: { is_included: e.target.value === '' ? null : e.target.value === 'y' } })}>
            <option value="">—</option>
            <option value="y">Included</option>
            <option value="n">Not included</option>
          </select>
        </td>
      )}
    />
  )
}

/** The shape both spares and BOM share: a parent from the committed lines, children under it. */
function ParentChild({ ex, add, patch, drop, exhibit, title, hint, childLabel, extraHead, extraCells }: Ctx & {
  exhibit: string
  title: string
  hint: string
  childLabel: string
  extraHead: React.ReactNode
  extraCells: (r: ExhibitItem) => React.ReactNode
}) {
  const rows = ex.items[exhibit] ?? []
  const [parent, setParent] = useState('')
  const [desc, setDesc] = useState('')
  const [qty, setQty] = useState<number | ''>('')
  const lines = ex.committed_lines
  const used = lines.filter((l) => rows.some((r) => r.scope_line_id === l.scope_line_id))

  return (
    <div>
      <Head ex={ex} title={title} />
      <div className="no-print" style={{ fontSize: 11, color: '#9aa0a6', marginBottom: 8 }}>{hint}</div>
      <div className="no-print" style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 10 }}>
        <div style={{ width: 280 }}>
          <label style={{ margin: '0 0 3px' }}>Parent Item <span style={{ color: 'var(--red)' }}>*</span></label>
          <select className="si" style={{ width: '100%' }} value={parent} onChange={(e) => setParent(e.target.value)}>
            <option value="">— pick a committed line —</option>
            {lines.map((l) => <option key={l.scope_line_id} value={l.scope_line_id}>{l.label} (×{l.qty})</option>)}
          </select>
        </div>
        <div style={{ width: 240 }}>
          <label style={{ margin: '0 0 3px' }}>{childLabel} <span style={{ color: 'var(--red)' }}>*</span></label>
          <input className="si" style={{ width: '100%' }} value={desc} onChange={(e) => setDesc(e.target.value)} />
        </div>
        <div style={{ width: 74 }}>
          <label style={{ margin: '0 0 3px' }}>Qty</label>
          <input className="si" style={{ width: '100%' }} type="number" value={qty} onChange={(e) => setQty(e.target.value === '' ? '' : Number(e.target.value))} />
        </div>
        <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }}
          onClick={() => { add({ exhibit, scope_line_id: parent, description: desc, qty: qty === '' ? null : Number(qty) }); setDesc(''); setQty('') }}
          disabled={!parent || !desc}>Add</button>
      </div>

      {used.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>Nothing entered yet.</div>}
      {used.map((l) => (
        <div key={l.scope_line_id} style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 700, background: 'var(--soft)', padding: '5px 7px', borderRadius: 6 }}>
            {l.label} <span style={{ fontWeight: 400, color: 'var(--mut)' }}>×{l.qty}</span>
          </div>
          <table>
            <thead><tr><th>{childLabel}</th><th className="num">Qty</th>{extraHead}<th>Notes</th><th className="no-print" /></tr></thead>
            <tbody>
              {rows.filter((r) => r.scope_line_id === l.scope_line_id).map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.description}</strong></td>
                  <td className="num">
                    <input className="si" style={{ width: 56, textAlign: 'right' }} type="number" defaultValue={r.qty ?? ''}
                      onBlur={(e) => patch({ id: r.id, patch: { qty: e.target.value ? Number(e.target.value) : null } })} />
                  </td>
                  {extraCells(r)}
                  <td>
                    <input className="si" style={{ width: '100%' }} defaultValue={r.note ?? ''}
                      onBlur={(e) => patch({ id: r.id, patch: { note: e.target.value || null } })} />
                  </td>
                  <td className="num no-print"><button className="btn sm danger" onClick={() => drop(r.id)}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

/** Shipping capacity — per equipment type, buildings down, months across, from a confirmed ROJ. */
function Capacity({ ex, add, patch, drop }: Ctx) {
  const types = ex.equipment_types.filter((o) => o.equipment_type_id)
  const [typeId, setTypeId] = useState(types[0]?.equipment_type_id ?? '')
  const [start, setStart] = useState(ex.roj_dates[0] ?? '')
  const rows = (ex.items.shipping_capacity ?? []).filter((r) => r.equipment_type_id === typeId)
  const chosen = types.find((o) => o.equipment_type_id === typeId)

  const places: { building: string; area: string | null }[] = [
    ...new Map(
      ex.committed_lines
        .filter((l) => l.equipment_type_id === typeId && l.building)
        .map((l) => [`${l.building}|${l.area ?? ''}`, { building: l.building as string, area: l.area }])
    ).values(),
  ]
  const months = start ? monthsFrom(start, 12) : []
  const cell = (b: string, a: string | null, m: string) =>
    rows.find((r) => r.building === b && (r.area ?? '') === (a ?? '') && r.due_date === m)
  const scheduled = rows.reduce((n, r) => n + (r.qty ?? 0), 0)
  const need = chosen?.unit_count ?? 0

  const setCell = (b: string, a: string | null, m: string, v: string) => {
    const existing = cell(b, a, m)
    const n = v === '' ? null : Number(v)
    if (existing && n == null) return drop(existing.id)
    if (existing) return patch({ id: existing.id, patch: { qty: n } })
    if (n != null) add({ exhibit: 'shipping_capacity', equipment_type_id: typeId, building: b, area: a, due_date: m, qty: n, description: `${b}${a ? ` · ${a}` : ''} capacity` })
  }

  return (
    <div>
      <Head ex={ex} title="SHIPPING CAPACITY & REQUIRED RELEASE BY" />
      <div className="no-print" style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 8 }}>
        <div style={{ width: 240 }}>
          <label style={{ margin: '0 0 3px' }}>Vendor Item (equipment type)</label>
          <select className="si" style={{ width: '100%' }} value={typeId} onChange={(e) => setTypeId(e.target.value ?? '')}>
            {types.map((o) => <option key={o.equipment_type_id} value={o.equipment_type_id ?? ''}>{o.label} ({o.unit_count})</option>)}
          </select>
        </div>
        <div style={{ width: 180 }}>
          <label style={{ margin: '0 0 3px' }}>Start Date (confirmed ROJ)</label>
          <select className="si" style={{ width: '100%' }} value={start} onChange={(e) => setStart(e.target.value)} disabled={ex.roj_dates.length === 0}>
            <option value="">{ex.roj_dates.length === 0 ? '— none confirmed yet —' : '— pick —'}</option>
            {ex.roj_dates.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div style={{ fontSize: 12, paddingBottom: 6 }}>
          Equipment List Qty <strong>{need}</strong> · Total Scheduled <strong>{scheduled}</strong>{' '}
          <span style={{ color: scheduled === need && need > 0 ? 'var(--accent)' : 'var(--amber)' }}>
            {need === 0 ? '' : scheduled === need ? '· OK — fully scheduled' : `· ${need - scheduled} unscheduled`}
          </span>
        </div>
      </div>
      {ex.roj_dates.length === 0 && (
        <div className="note">
          Capacity starts from a date already confirmed on the delivery schedule — enter the ROJ dates first.
        </div>
      )}
      {start && places.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ minWidth: 700 }}>
            <thead><tr>
              <th>Shipping Capacity (units/mo)</th>
              {months.map((m) => <th key={m} className="num" style={{ whiteSpace: 'nowrap' }}>{m.slice(0, 7)}</th>)}
              <th className="num">Total</th>
            </tr></thead>
            <tbody>
              {places.map((p) => {
                const rowTotal = months.reduce((n, m) => n + (cell(p.building, p.area, m)?.qty ?? 0), 0)
                return (
                  <tr key={`${p.building}|${p.area ?? ''}`}>
                    <td><strong>{p.building}</strong>{p.area ? <span style={{ color: 'var(--mut)' }}> · {p.area}</span> : null}</td>
                    {months.map((m) => (
                      <td key={m} className="num">
                        <input className="si" style={{ width: 46, textAlign: 'right', padding: '4px 5px' }} type="number"
                          defaultValue={cell(p.building, p.area, m)?.qty ?? ''}
                          onBlur={(e) => setCell(p.building, p.area, m, e.target.value)} />
                      </td>
                    ))}
                    <td className="num"><strong>{rowTotal || ''}</strong></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function monthsFrom(start: string, n: number): string[] {
  const d = new Date(start + 'T00:00:00')
  return Array.from({ length: n }, (_, i) => {
    const m = new Date(d.getFullYear(), d.getMonth() + i, 1)
    return `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}-01`
  })
}

/** Schedule D — a document per equipment type, owed at a named trigger. */
function Documents({ ex, add, patch, drop }: Ctx) {
  const rows = ex.items.required_documents ?? []
  const types = ex.equipment_types.filter((o) => o.equipment_type_id)
  const [typeId, setTypeId] = useState('')
  const [name, setName] = useState('')
  const [gate, setGate] = useState(GATES[0])
  const [needBy, setNeedBy] = useState('')
  const label = (id: string | null) => types.find((o) => o.equipment_type_id === id)?.label

  return (
    <div>
      <Head ex={ex} title="SCHEDULE D — CONTRACT DOCUMENTS" />
      <div className="no-print" style={{ fontSize: 11, color: '#9aa0a6', marginBottom: 8 }}>
        Per equipment type, not per unit. The trigger is the column with teeth — "Prior to Final
        Payment" is retainage.
      </div>
      <div className="no-print" style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 10 }}>
        <div style={{ width: 220 }}>
          <label style={{ margin: '0 0 3px' }}>Equipment Type</label>
          <select className="si" style={{ width: '100%' }} value={typeId} onChange={(e) => setTypeId(e.target.value)}>
            <option value="">all on this PO</option>
            {types.map((o) => <option key={o.equipment_type_id} value={o.equipment_type_id ?? ''}>{o.label}</option>)}
          </select>
        </div>
        <div style={{ width: 230 }}>
          <label style={{ margin: '0 0 3px' }}>Document Name <span style={{ color: 'var(--red)' }}>*</span></label>
          <input className="si" style={{ width: '100%' }} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div style={{ width: 210 }}>
          <label style={{ margin: '0 0 3px' }}>Trigger / Activity <span style={{ color: 'var(--red)' }}>*</span></label>
          <select className="si" style={{ width: '100%' }} value={gate} onChange={(e) => setGate(e.target.value)}>
            {GATES.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
        <div style={{ width: 140 }}>
          <label style={{ margin: '0 0 3px' }}>Need-By Date</label>
          <input className="si" style={{ width: '100%' }} type="date" value={needBy} onChange={(e) => setNeedBy(e.target.value)} />
        </div>
        <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }}
          onClick={() => { add({ exhibit: 'required_documents', description: name, gate, equipment_type_id: typeId || null, due_date: needBy || null, is_required: true }); setName(''); setNeedBy('') }}
          disabled={!name}>Add</button>
      </div>

      {rows.length === 0
        ? <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No documents scheduled yet.</div>
        : <table>
            <thead><tr><th>Equipment Type</th><th>Document Name</th><th>Required?</th><th>Need-By Date</th><th>Trigger / Activity</th><th>Notes</th><th className="no-print" /></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.equipment_type_id ? label(r.equipment_type_id) : <span style={{ color: 'var(--mut)' }}>all on this PO</span>}</td>
                  <td><strong>{r.description}</strong></td>
                  <td>
                    <select className="si" value={r.is_required === false ? 'n' : 'y'}
                      onChange={(e) => patch({ id: r.id, patch: { is_required: e.target.value === 'y' } })}>
                      <option value="y">Yes</option><option value="n">No</option>
                    </select>
                  </td>
                  <td>
                    <input className="si" type="date" defaultValue={r.due_date ?? ''}
                      onBlur={(e) => patch({ id: r.id, patch: { due_date: e.target.value || null } })} />
                  </td>
                  <td style={{ color: r.gate === 'Prior to Final Payment' ? 'var(--red)' : 'var(--amber)', fontSize: 12 }}>{r.gate}</td>
                  <td>
                    <input className="si" style={{ width: '100%' }} defaultValue={r.note ?? ''}
                      onBlur={(e) => patch({ id: r.id, patch: { note: e.target.value || null } })} />
                  </td>
                  <td className="num no-print"><button className="btn sm danger" onClick={() => drop(r.id)}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>}
    </div>
  )
}

function Legend({ ex }: { ex: ExhibitSet }) {
  return (
    <div>
      <Head ex={ex} title="ASSET REGISTRY LEGEND" />
      {ex.legend.length === 0
        ? <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No codes on the project yet.</div>
        : <table>
            <thead><tr><th style={{ width: 110 }}>Kind</th><th style={{ width: 120 }}>Code</th><th>Description</th></tr></thead>
            <tbody>
              {ex.legend.map((l) => (
                <tr key={`${l.kind}-${l.code}`}>
                  <td style={{ color: 'var(--mut)' }}>{l.kind}</td>
                  <td><strong>{l.code}</strong></td>
                  <td style={{ color: 'var(--mut)' }}>{l.description ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>}
    </div>
  )
}

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
        As read off the signed document. Leave a field blank if you didn't read it — blank means
        "not stated", which is different from "disagrees".
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
        <>
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
          <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 4 }}>
            Flagged, never applied. The record still holds what it committed.
          </div>
        </>
      )}
    </div>
  )
}

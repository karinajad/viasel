import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from './services/api'
import { resolveSpec, subTypesFor, unitTypeCodes } from './lib/equipment'
import { locationOptions } from './lib/locations'
import { count } from './lib/format'
import type { DemandLineCreate, DemandLineRow, EquipmentType, ProjectLocation } from './types/rom'

/**
 * The Design register — what is needed, where, how many, by when.
 *
 * No cost. Design declares the requirement; pricing it is a separate act on a separate
 * face, and a derived one. Putting a ROM column here made data entry wait on the price
 * engine and made the register look like an estimate.
 */
interface Row {
  key: number
  type: string
  sub: string
  qty: number
  locId: string
  requiredBy: string
  leadWeeks: number | ''
}

let nextKey = 1
const blank = (type = '', sub = '', leadWeeks: number | '' = ''): Row =>
  ({ key: nextKey++, type, sub, qty: 1, locId: '', requiredBy: '', leadWeeks })
const isComplete = (r: Row): boolean => r.type !== '' && r.qty >= 1

export default function DesignRegister({ project, projectId }: { project: string; projectId?: string }) {
  const qc = useQueryClient()
  const typesQ = useQuery({ queryKey: ['equipment-types'], queryFn: () => apiGet<EquipmentType[]>('/equipment-types') })
  const types = useMemo(() => typesQ.data ?? [], [typesQ.data])
  const codes = useMemo(() => unitTypeCodes(types), [types])

  const locQ = useQuery({
    queryKey: ['locations', projectId],
    queryFn: () => apiGet<ProjectLocation[]>(`/projects/${projectId}/locations`),
    enabled: !!projectId,
  })
  const locOpts = useMemo(() => locationOptions(locQ.data ?? []), [locQ.data])

  const [rows, setRows] = useState<Row[]>(() => [blank(), blank(), blank()])
  const [saved, setSaved] = useState(0)

  const editRow = (key: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)))
  const addRow = () => {
    const last = rows[rows.length - 1]
    setRows((rs) => [...rs, blank(last?.type ?? codes[0] ?? '', last?.sub ?? '', last?.leadWeeks ?? '')])
  }
  const dupRow = (r: Row) =>
    setRows((rs) => rs.flatMap((x) => (x.key === r.key ? [x, { ...x, key: nextKey++, locId: '' }] : [x])))
  const dropRow = (key: number) =>
    setRows((rs) => (rs.length === 1 ? [blank()] : rs.filter((r) => r.key !== key)))

  const specOf = (r: Row) => resolveSpec(types, r.type, r.sub)
  const complete = rows.filter(isComplete)
  const totalQty = complete.reduce((n, r) => n + r.qty, 0)
  const longest = complete.reduce((n, r) => Math.max(n, Number(r.leadWeeks) || 0), 0)

  const saveM = useMutation({
    mutationFn: () => {
      const lines: DemandLineCreate[] = complete.map((r) => {
        const s = specOf(r)
        const loc = locOpts.find((o) => o.id === r.locId)
        return {
          project_id: project,
          qty: r.qty,
          equipment_type_id: s.row?.id ?? null,
          spec_attributes: { type_query: r.type, denominator: s.denominator, size: s.size, sub: s.subType },
          target_building: loc?.building ?? null,
          target_area: loc?.area ?? null,
          required_by_date: r.requiredBy || null,
          lead_time_weeks: r.leadWeeks === '' ? null : Number(r.leadWeeks),
          // no ROM — pricing is the ROM face's job, over the saved record
          rom_unit_price: null,
          rom_confidence: null,
          rom_comparables_count: null,
        }
      })
      return apiPost<DemandLineRow[]>('/demand-lines/batch', { lines })
    },
    onSuccess: (created) => {
      setSaved(created.length)
      setRows([blank(), blank(), blank()])
      qc.invalidateQueries({ queryKey: ['demand-lines'] })
      qc.invalidateQueries({ queryKey: ['freeze-preview'] })
    },
  })

  return (
    <div className="card">
      <h4 style={{ margin: 0 }}>Design register · {project}</h4>
      <p style={{ fontSize: 12, color: 'var(--mut)', margin: '4px 0 12px' }}>
        What is needed, where, how many, by when, and how long it takes. No cost here — the ROM prices
        this once it's on the record, and a requirement is real whether or not history can price it.
      </p>

      {locOpts.length === 0 && (
        <div className="note" style={{ marginTop: 0, marginBottom: 10 }}>
          No building / area codes for <strong>{project}</strong> yet — add them on the <strong>Projects</strong> tab
          and they'll appear in the Location dropdown.
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th style={{ width: 26 }} />
            <th>Type</th>
            <th>Size / configuration</th>
            <th className="num" style={{ width: 64 }}>Qty</th>
            <th>Location</th>
            <th style={{ width: 138 }}>Required by</th>
            <th className="num" style={{ width: 104 }} title="the design-side lead-time assumption — what turns a required-by date into a must-buy-by date">Long lead (wks)</th>
            <th style={{ width: 56 }} />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const subs = subTypesFor(types, r.type)
            const s = specOf(r)
            return (
              <tr key={r.key}>
                <td style={{ color: 'var(--mut)', fontSize: 11 }}>{i + 1}</td>
                <td>
                  <select className="si" style={{ width: '100%' }} value={r.type} onChange={(e) => editRow(r.key, { type: e.target.value, sub: '' })} disabled={typesQ.isLoading}>
                    <option value="">{typesQ.isLoading ? 'loading…' : '— pick a type —'}</option>
                    {codes.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </td>
                <td>
                  <select className="si" style={{ width: '100%' }} value={s.subType} onChange={(e) => editRow(r.key, { sub: e.target.value })} disabled={subs.length === 0}>
                    {subs.length === 0 && <option value="">{r.type ? '— none on record —' : '—'}</option>}
                    {subs.map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                </td>
                <td className="num">
                  <input className="si" style={{ width: 58, textAlign: 'right' }} type="number" min={1} value={r.qty} onChange={(e) => editRow(r.key, { qty: Number(e.target.value) })} />
                </td>
                <td>
                  <select className="si" style={{ width: '100%' }} value={r.locId} onChange={(e) => editRow(r.key, { locId: e.target.value })} disabled={locOpts.length === 0}>
                    <option value="">— unassigned —</option>
                    {locOpts.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </select>
                </td>
                <td>
                  <input className="si" style={{ width: '100%' }} type="date" value={r.requiredBy} onChange={(e) => editRow(r.key, { requiredBy: e.target.value })} />
                </td>
                <td className="num">
                  <input className="si" style={{ width: 62, textAlign: 'right' }} type="number" min={0}
                    value={r.leadWeeks} onChange={(e) => editRow(r.key, { leadWeeks: e.target.value === '' ? '' : Number(e.target.value) })} />
                </td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  <button className="btn sm" title="duplicate row" onClick={() => dupRow(r)}>⧉</button>{' '}
                  <button className="btn sm danger" title="remove row" onClick={() => dropRow(r.key)}>✕</button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
        <button className="btn sm" onClick={addRow}>+ Add row</button>
        <button className="btn pri" onClick={() => saveM.mutate()} disabled={complete.length === 0 || saveM.isPending}>
          {saveM.isPending ? 'Saving…' : `Save ${count(complete.length, 'line')} to the register ▸`}
        </button>
        {complete.length > 0 && (
          <span style={{ fontSize: 12, color: 'var(--mut)' }}>
            {count(totalQty, 'unit')}{longest > 0 && <> · longest lead {longest} weeks</>}
          </span>
        )}
        {saved > 0 && <span style={{ fontSize: 12, color: 'var(--accent)' }}>✓ {count(saved, 'line')} on the register — price them on the ROM tab, then freeze below.</span>}
        {saveM.isError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{String(saveM.error).replace(/^Error:\s*/, '')}</span>}
      </div>
    </div>
  )
}

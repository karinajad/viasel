import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from './services/api'
import { resolveSpec, subTypesFor, unitTypeCodes } from './lib/equipment'
import { locationOptions } from './lib/locations'
import { TIER, money } from './lib/format'
import type {
  DemandLineCreate,
  DemandLineRow,
  EquipmentType,
  ProjectLocation,
  RomBand,
  RomPriceBatchResponse,
} from './types/rom'

/** One row of the grid — what it is, how many, where it goes, and its price once ROMed. */
interface Row {
  key: number
  type: string
  sub: string
  qty: number
  locId: string
  band: RomBand | null
}

let nextKey = 1
const blank = (type = '', sub = ''): Row => ({ key: nextKey++, type, sub, qty: 1, locId: '', band: null })
const isPriceable = (r: Row): boolean => r.type !== '' && r.qty >= 1

export default function RomGrid({ project, projectId }: { project: string; projectId?: string }) {
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
  const [escalation, setEscalation] = useState(0)
  const [tariff, setTariff] = useState(0)
  const [result, setResult] = useState<RomPriceBatchResponse | null>(null)
  const [stale, setStale] = useState(false) // the list changed since it was priced
  const [saved, setSaved] = useState(0)

  // an edited row's own price is void, and so is the total — nothing stale is shown as current
  const editRow = (key: number, patch: Partial<Row>) => {
    const voids = 'type' in patch || 'sub' in patch || 'qty' in patch
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch, band: voids ? null : r.band } : r)))
    if (voids) setStale(true)
  }
  const addRow = () => {
    const last = rows[rows.length - 1]
    setRows((rs) => [...rs, blank(last?.type ?? codes[0] ?? '', last?.sub ?? '')])
    setStale(true)
  }
  const dupRow = (r: Row) => {
    setRows((rs) => rs.flatMap((x) => (x.key === r.key ? [x, { ...x, key: nextKey++, locId: '' }] : [x])))
    setStale(true)
  }
  const dropRow = (key: number) => {
    setRows((rs) => (rs.length === 1 ? [blank()] : rs.filter((r) => r.key !== key)))
    setStale(true)
  }

  const specOf = (r: Row) => resolveSpec(types, r.type, r.sub)
  const priceable = rows.filter(isPriceable)

  const priceM = useMutation({
    mutationFn: () =>
      apiPost<RomPriceBatchResponse>('/rom/price-batch', {
        lines: priceable.map((r) => {
          const s = specOf(r)
          return { type_query: r.type, denominator: s.denominator, size: s.size, qty: r.qty }
        }),
        escalation_pct: escalation / 100,
        tariff_pct: tariff / 100,
      }),
    onSuccess: (res) => {
      // bands come back in request order — map them onto the rows that were sent
      const byKey = new Map(priceable.map((r, i) => [r.key, res.lines[i] ?? null]))
      setRows((rs) => rs.map((r) => (byKey.has(r.key) ? { ...r, band: byKey.get(r.key) ?? null } : r)))
      setResult(res)
      setStale(false)
      setSaved(0)
    },
  })

  const saveM = useMutation({
    mutationFn: () => {
      const lines: DemandLineCreate[] = priceable.map((r) => {
        const s = specOf(r)
        const loc = locOpts.find((o) => o.id === r.locId)
        return {
          project_id: project,
          qty: r.qty,
          equipment_type_id: s.row?.id ?? null,
          spec_attributes: { type_query: r.type, denominator: s.denominator, size: s.size, sub: s.subType },
          target_building: loc?.building ?? null,
          target_area: loc?.area ?? null,
          rom_unit_price: r.band?.unit_mid ?? null,
          rom_confidence: r.band?.confidence_tier ?? null,
          rom_comparables_count: r.band?.comparables_count ?? null,
        }
      })
      return apiPost<DemandLineRow[]>('/demand-lines/batch', { lines })
    },
    onSuccess: (created) => {
      setSaved(created.length)
      setRows([blank(), blank(), blank()])
      setResult(null)
      setStale(false)
      qc.invalidateQueries({ queryKey: ['demand-lines'] })
    },
  })

  const roll = result?.rollup
  const unpricedRows = priceable.filter((r) => r.band?.unit_mid == null).length
  const dim = stale ? 0.4 : 1

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
        <h4 style={{ margin: 0 }}>Line-item list · {project}</h4>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 11, color: 'var(--mut)' }}>
          <span>escalation</span>
          <input className="si" style={{ width: 58 }} type="number" value={escalation} onChange={(e) => { setEscalation(Number(e.target.value)); setStale(true) }} />
          <span>% · tariff</span>
          <input className="si" style={{ width: 58 }} type="number" value={tariff} onChange={(e) => { setTariff(Number(e.target.value)); setStale(true) }} />
          <span>%</span>
        </div>
      </div>

      {locOpts.length === 0 && (
        <div className="note" style={{ marginTop: 0, marginBottom: 10 }}>
          No building / area codes for <strong>{project}</strong> yet — add them on the <strong>Projects</strong> tab and they’ll appear in the Location dropdown.
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
            <th className="num">ROM / unit</th>
            <th className="num">Extended</th>
            <th style={{ width: 70 }}>Conf.</th>
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
                <td className="num">{money(r.band?.unit_mid)}</td>
                <td className="num">{money(r.band?.unit_mid == null ? null : r.band.unit_mid * r.qty)}</td>
                <td>
                  {r.band && (
                    <span style={{ fontSize: 11, fontWeight: 600, color: TIER[r.band.confidence_tier] }}>
                      {r.band.confidence_tier}
                      <span style={{ color: 'var(--mut)', fontWeight: 400 }}> · {r.band.comparables_count}</span>
                    </span>
                  )}
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

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
        <button className="btn sm" onClick={addRow}>+ Add row</button>
        <button className="btn pri" onClick={() => priceM.mutate()} disabled={priceable.length === 0 || priceM.isPending}>
          {priceM.isPending ? 'Pricing…' : `Price all ${priceable.length} lines`}
        </button>
        {stale && result && <span style={{ fontSize: 12, color: 'var(--red)' }}>list changed — price it again</span>}
        {priceM.isError && <span style={{ fontSize: 12, color: 'var(--red)' }}>Couldn’t reach the API (backend on :8000, key set?).</span>}
        {saved > 0 && <span style={{ fontSize: 12, color: 'var(--accent)' }}>✓ {saved} lines saved as drafted demand — freeze them below.</span>}
      </div>

      {roll && (
        <div style={{ marginTop: 14 }}>
          <div className="band">
            <div style={{ opacity: dim }}>
              <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)', marginBottom: 4 }}>
                Work-in-progress project ROM
              </div>
              <div className="nums">
                <span>{money(roll.total_low)}</span>
                <span className="mid">{money(roll.total_mid)}</span>
                <span>{money(roll.total_high)}</span>
              </div>
              <div className="track" />
              <div style={{ fontSize: 12, color: 'var(--mut)' }}>
                {roll.line_count} lines · {roll.total_qty} units · confidence{' '}
                <strong style={{ color: TIER[roll.confidence_tier] }}>{roll.confidence_tier}</strong>
                <span style={{ color: '#9aa0a6' }}> (the weakest line sets it)</span>
              </div>
            </div>
            {roll.unpriced_count > 0 && (
              <div className="note">
                {roll.unpriced_count} of {roll.line_count} lines have no comparables in the executed record — they add nothing to this total. Fall back to quotes or judgment for those.
              </div>
            )}
            <button
              className="btn"
              style={{ marginTop: 12, width: '100%', borderColor: 'var(--accent)', color: 'var(--accent)' }}
              onClick={() => saveM.mutate()}
              disabled={saveM.isPending || priceable.length === 0}
            >
              {saveM.isPending ? 'Saving…' : `Save all ${priceable.length} lines as demand ▸`}
            </button>
            {unpricedRows > 0 && (
              <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 6 }}>
                {unpricedRows} line{unpricedRows === 1 ? '' : 's'} will save without a ROM — the requirement is real either way.
              </div>
            )}
          </div>
        </div>
      )}
      {saveM.isError && <div className="note">Couldn’t save the lines — is the backend up?</div>}
    </div>
  )
}

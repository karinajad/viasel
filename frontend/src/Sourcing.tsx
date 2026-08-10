import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPost } from './services/api'
import { STATE, money, physics, signed, signedPct } from './lib/format'
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
        <Packages project={project} packages={pkgQ.data ?? []} loading={pkgQ.isLoading} />
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
                  <td className="num">{p.quote_count}</td>
                  <td><span className="st" style={{ background: p.state === 'awarded' ? 'var(--accent)' : '#6b7280' }}>{p.state}</span></td>
                  <td className="num">{p.awarded_vendor ? <>{p.awarded_vendor}<br /><span style={{ color: 'var(--mut)', fontSize: 11 }}>{money(p.awarded_extended)}</span></> : '—'}</td>
                  <td className="num">
                    <button className="btn sm" onClick={() => setOpen(open === p.id ? null : p.id)}>
                      {open === p.id ? 'Hide' : p.state === 'awarded' ? 'View ▸' : 'Level bids ▸'}
                    </button>
                  </td>
                </tr>
                {open === p.id && (
                  <tr><td colSpan={8} style={{ background: '#fafbfc' }}><PackagePanel packageId={p.id} project={project} /></td></tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function PackagePanel({ packageId, project }: { packageId: string; project: string }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['package', packageId], queryFn: () => apiGet<PackageDetail>(`/packages/${packageId}`) })
  const [vendor, setVendor] = useState('')
  const [oem, setOem] = useState('')
  const [unit, setUnit] = useState<number | ''>('')
  const [lead, setLead] = useState<number | ''>('')
  const [confirming, setConfirming] = useState<string | null>(null)

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['package', packageId] })
    qc.invalidateQueries({ queryKey: ['packages', project] })
  }
  const bidM = useMutation({
    mutationFn: () => apiPost<PackageDetail>(`/packages/${packageId}/quotes`, {
      vendor, oem: oem || null, unit_price: Number(unit), lead_time_weeks: lead === '' ? null : Number(lead),
    }),
    onSuccess: () => { setVendor(''); setOem(''); setUnit(''); setLead(''); refresh() },
  })
  const awardM = useMutation({
    mutationFn: (quoteId: string) => apiPost(`/packages/${packageId}/award`, { quote_id: quoteId }),
    onSuccess: () => { setConfirming(null); refresh(); qc.invalidateQueries({ queryKey: ['demand-lines'] }) },
  })
  const dropM = useMutation({
    mutationFn: (dlId: string) => apiDelete(`/packages/${packageId}/lines/${dlId}`),
    onSuccess: () => { refresh(); qc.invalidateQueries({ queryKey: ['candidates', project] }) },
  })

  if (q.isLoading || !q.data) return <div style={{ padding: 8, color: 'var(--mut)', fontSize: 12.5 }}>Loading…</div>
  const { package: pkg, lines, leveling } = q.data
  const awarded = pkg.state === 'awarded'

  return (
    <div style={{ padding: '8px 2px' }}>
      <Sub>Lot contents · {pkg.total_qty} units of {label(pkg)} across {pkg.line_count} lines</Sub>
      <table style={{ marginBottom: 14 }}>
        <thead><tr><th>Building / area</th><th className="num">Qty</th><th className="num">ROM / unit</th><th>Demand state</th><th /></tr></thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.demand_line_id}>
              <td>{l.target_building ?? 'unassigned'}{l.target_area ? ` · ${l.target_area}` : ''}</td>
              <td className="num">{l.qty}</td>
              <td className="num">{money(l.rom_unit_price)}</td>
              <td><span className="st" style={{ background: STATE[l.state] ?? '#6b7280' }}>{l.state}</span></td>
              <td className="num">
                {!awarded && lines.length > 1 && (
                  <button className="btn sm danger" title="drop from this lot" onClick={() => dropM.mutate(l.demand_line_id)} disabled={dropM.isPending}>✕</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Sub>Bid leveling · every bid per {pkg.denominator}, against the {money(pkg.rom_unit_price)}/unit the record already says</Sub>
      {!awarded && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
          <input className="si" style={{ width: 130 }} placeholder="Vendor" value={vendor} onChange={(e) => setVendor(e.target.value)} />
          <input className="si" style={{ width: 110 }} placeholder="OEM" value={oem} onChange={(e) => setOem(e.target.value)} />
          <input className="si" style={{ width: 120 }} type="number" placeholder="$ / unit" value={unit} onChange={(e) => setUnit(e.target.value === '' ? '' : Number(e.target.value))} />
          <input className="si" style={{ width: 96 }} type="number" placeholder="Lead (wk)" value={lead} onChange={(e) => setLead(e.target.value === '' ? '' : Number(e.target.value))} />
          <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }} onClick={() => bidM.mutate()} disabled={!vendor || unit === '' || bidM.isPending}>Add bid</button>
        </div>
      )}

      {leveling.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No bids yet.</div>}
      {leveling.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Vendor</th>
              <th className="num">$ / unit</th>
              <th className="num">per {pkg.denominator}</th>
              <th className="num">Lead</th>
              <th className="num">Extended ({pkg.total_qty})</th>
              <th className="num">vs lowest</th>
              <th className="num">vs ROM</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {leveling.map((r) => (
              <tr key={r.quote_id} style={{ background: r.is_selected ? '#eef7f0' : 'transparent' }}>
                <td>
                  <strong>{r.vendor}</strong>{r.oem && <span style={{ color: 'var(--mut)' }}> · {r.oem}</span>}
                  {r.is_low && !awarded && <span style={{ color: 'var(--accent)', fontSize: 11 }}> · lowest</span>}
                  {r.is_selected && <span style={{ color: 'var(--accent)', fontSize: 11, fontWeight: 600 }}> · awarded</span>}
                </td>
                <td className="num">{money(r.unit_price)}</td>
                <td className="num">{money(r.normalized)}</td>
                <td className="num">{r.lead_time_weeks ?? '—'}</td>
                <td className="num">{money(r.extended)}</td>
                <td className="num" style={{ color: r.delta_vs_low === 0 ? 'var(--accent)' : 'var(--mut)' }}>
                  {r.delta_vs_low === 0 ? '—' : `${signed(r.delta_vs_low)}${signedPct(r.delta_vs_low_pct)}`}
                </td>
                <td className="num" style={{ color: r.delta_vs_rom == null ? 'var(--mut)' : r.delta_vs_rom > 0 ? 'var(--red)' : 'var(--accent)' }}>
                  {r.delta_vs_rom == null ? '—' : `${signed(r.delta_vs_rom)}${signedPct(r.delta_vs_rom_pct)}`}
                </td>
                <td className="num" style={{ whiteSpace: 'nowrap' }}>
                  {!awarded && confirming !== r.quote_id && (
                    <button className="btn sm" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => setConfirming(r.quote_id)}>Award ▸</button>
                  )}
                  {!awarded && confirming === r.quote_id && (
                    <>
                      <button className="btn sm pri" onClick={() => awardM.mutate(r.quote_id)} disabled={awardM.isPending}>
                        {awardM.isPending ? 'Awarding…' : `Commit ${money(r.extended)}`}
                      </button>{' '}
                      <button className="btn sm" onClick={() => setConfirming(null)}>Cancel</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
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
      {bidM.isError && <div className="note">Couldn’t add that bid — {String(bidM.error)}</div>}
      {awardM.isError && <div className="note">Couldn’t award — {String(awardM.error)}</div>}
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

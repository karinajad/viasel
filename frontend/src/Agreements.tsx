import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from './services/api'
import { count, money } from './lib/format'
import Exhibits from './Exhibits'
import type { Agreement } from './types/agreement'
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


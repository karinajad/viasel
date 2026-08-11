import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from './services/api'
import { count, money } from './lib/format'
import type { Agreement, ExhibitSet } from './types/agreement'
import type { PackageRead } from './types/sourcing'

const STATE_COLOR: Record<string, string> = {
  draft: '#6b7280', issued: '#b7791f', executed: '#2f6f4f', cancelled: '#9aa0a6',
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
            <thead><tr><th>PO number</th><th>Vendor</th><th className="num">Lines</th><th className="num">Units</th><th className="num">Contract value</th><th>State</th><th>Executed</th><th /></tr></thead>
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
                    <td style={{ color: a.execution_date ? 'var(--ink)' : 'var(--line)' }}>{a.execution_date ?? '—'}</td>
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
  const [execDate, setExecDate] = useState('')
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['exhibits', agreementId] })
    qc.invalidateQueries({ queryKey: ['agreements', project] })
  }
  const issueM = useMutation({ mutationFn: () => apiPost(`/agreements/${agreementId}/issue`, { issued_date: new Date().toISOString().slice(0, 10) }), onSuccess: refresh })
  const execM = useMutation({ mutationFn: () => apiPost(`/agreements/${agreementId}/execute`, { execution_date: execDate }), onSuccess: refresh })

  if (q.isLoading || !q.data) return <div style={{ padding: 8, color: 'var(--mut)', fontSize: 12.5 }}>Loading…</div>
  const { agreement: a, cover_sheet: c, equipment_list: rows, legend, not_yet_derivable: gaps } = q.data
  const listTotal = rows.reduce((n, r) => n + r.extended_price, 0)

  return (
    <div style={{ padding: '8px 2px' }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        {a.state === 'draft' && <button className="btn sm" onClick={() => issueM.mutate()} disabled={issueM.isPending}>Issue to vendor ▸</button>}
        {a.state === 'issued' && (
          <>
            <input className="si" type="date" value={execDate} onChange={(e) => setExecDate(e.target.value)} />
            <button className="btn pri sm" onClick={() => execM.mutate()} disabled={!execDate || execM.isPending}>Record execution</button>
          </>
        )}
        {a.state === 'executed' && (
          <span style={{ fontSize: 12, color: 'var(--mut)' }}>
            Executed {a.execution_date}. Next: retrieve the signed document and reconcile it field-by-field
            against this — divergence flagged, never auto-corrected.
          </span>
        )}
        {(issueM.isError || execM.isError) && (
          <span style={{ fontSize: 12, color: 'var(--red)' }}>{String(issueM.error ?? execM.error).replace(/^Error:\s*/, '')}</span>
        )}
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
        PO <strong style={{ color: 'var(--ink)' }}>{c.po_number}</strong> · issued {c.date_of_issue ?? '—'}
      </div>

      <Sub>Exhibit A — equipment list</Sub>
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

      <Sub>Exhibit — legend</Sub>
      {legend.length === 0
        ? <div style={{ color: 'var(--mut)', fontSize: 12.5, marginBottom: 14 }}>No codes on the project yet.</div>
        : <table style={{ marginBottom: 14 }}>
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

      <div className="note">
        <strong>Not yet derivable from the record</strong> — named rather than left blank, because a blank in
        an executed exhibit reads as "nothing required":
        <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {gaps.map((g) => <li key={g} style={{ fontSize: 12 }}>{g}</li>)}
        </ul>
      </div>
    </div>
  )
}

function Sub({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)', marginBottom: 6 }}>{children}</div>
}

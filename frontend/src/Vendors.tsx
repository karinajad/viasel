import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPatch, apiPost } from './services/api'
import { count } from './lib/format'
import { VENDOR_ROLES, VENDOR_STATUSES } from './types/vendor'
import type { Vendor, VendorDetail } from './types/vendor'

const STATUS_COLOR: Record<string, string> = {
  preferred: '#2f6f4f', approved: '#2f6f4f', prospect: '#6b7280',
  hold: '#b7791f', disqualified: '#b23a3a',
}

/**
 * The vendor roster. Free-typed vendor names are why vendor reliability can never
 * accumulate — "Eaton" and "Eaton Corp" are two vendors, so a quoted lead time never
 * lines up with an actual delivery. One record per firm fixes that.
 */
export default function VendorsFace() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['vendors'], queryFn: () => apiGet<Vendor[]>('/vendors') })
  const vendors = q.data ?? []
  const [open, setOpen] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [role, setRole] = useState('supplier')
  const [code, setCode] = useState('')

  const addM = useMutation({
    mutationFn: () => apiPost<Vendor>('/vendors', { name, role, code: code || null }),
    onSuccess: (v) => { setName(''); setCode(''); setOpen(v.id); qc.invalidateQueries({ queryKey: ['vendors'] }) },
  })

  return (
    <div>
      <div className="headline"><h2>Vendors</h2><span className="pill live">LIVE · Supabase</span></div>
      <p className="desc">
        One record per firm. Who they are, who actually manufactures, where it's built and integrated —
        because the executed record shows the route driving the spread more than anything else, and
        reliability can only accumulate against a stable identity.
      </p>

      <div className="card">
        <h4 style={{ margin: 0 }}>① Roster</h4>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end', margin: '10px 0' }}>
          <div style={{ width: 200 }}><label style={{ margin: '0 0 3px' }}>Vendor name</label>
            <input className="si" style={{ width: '100%' }} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Parrish Hare" /></div>
          <div style={{ width: 90 }}><label style={{ margin: '0 0 3px' }}>Code</label>
            <input className="si" style={{ width: '100%' }} value={code} onChange={(e) => setCode(e.target.value)} placeholder="PH" /></div>
          <div style={{ width: 140 }}><label style={{ margin: '0 0 3px' }}>Role</label>
            <select className="si" style={{ width: '100%' }} value={role} onChange={(e) => setRole(e.target.value)}>
              {VENDOR_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select></div>
          <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }}
            onClick={() => addM.mutate()} disabled={!name || addM.isPending}>Add vendor</button>
          {addM.isError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{String(addM.error).replace(/^Error:\s*/, '')}</span>}
        </div>

        {q.isLoading && <p style={{ color: 'var(--mut)', fontSize: 13 }}>Loading…</p>}
        {!q.isLoading && vendors.length === 0 && (
          <p style={{ color: 'var(--mut)', fontSize: 13 }}>No vendors yet. Add the firms you actually buy from.</p>
        )}
        {vendors.length > 0 && (
          <table>
            <thead><tr><th>Vendor</th><th>Role</th><th>Manufactures</th><th>Built / integrated</th><th>Status</th><th /></tr></thead>
            <tbody>
              {vendors.map((v) => (
                <Fragment key={v.id}>
                  <tr>
                    <td><strong>{v.name}</strong>{v.code && <span style={{ color: 'var(--mut)' }}> · {v.code}</span>}</td>
                    <td style={{ color: 'var(--mut)' }}>{v.role}</td>
                    <td style={{ color: 'var(--mut)' }}>{v.oem_names?.length ? v.oem_names.join(' · ') : v.role === 'oem' ? 'itself' : '—'}</td>
                    <td style={{ color: 'var(--mut)' }}>
                      {v.factory_location ?? v.factory_country ?? '—'}
                      {v.integration_location && <> → {v.integration_location}</>}
                    </td>
                    <td><span className="st" style={{ background: STATUS_COLOR[v.status] ?? '#6b7280' }}>{v.status}</span></td>
                    <td className="num"><button className="btn sm" onClick={() => setOpen(open === v.id ? null : v.id)}>{open === v.id ? 'Hide' : 'Edit ▸'}</button></td>
                  </tr>
                  {open === v.id && <tr><td colSpan={6} style={{ background: '#fafbfc' }}><VendorPanel vendorId={v.id} /></td></tr>}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function VendorPanel({ vendorId }: { vendorId: string }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['vendor', vendorId], queryFn: () => apiGet<VendorDetail>(`/vendors/${vendorId}`) })
  const [draft, setDraft] = useState<Record<string, unknown>>({})
  const [cname, setCname] = useState('')
  const [ctitle, setCtitle] = useState('')
  const [cemail, setCemail] = useState('')
  const invalidate = () => {
    setDraft({})
    qc.invalidateQueries({ queryKey: ['vendor', vendorId] })
    qc.invalidateQueries({ queryKey: ['vendors'] })
  }
  const saveM = useMutation({ mutationFn: () => apiPatch(`/vendors/${vendorId}`, draft), onSuccess: invalidate })
  const addC = useMutation({
    mutationFn: () => apiPost(`/vendors/${vendorId}/contacts`, { name: cname, title: ctitle || null, email: cemail || null }),
    onSuccess: () => { setCname(''); setCtitle(''); setCemail(''); invalidate() },
  })
  const delC = useMutation({ mutationFn: (id: string) => apiDelete(`/vendors/${vendorId}/contacts/${id}`), onSuccess: invalidate })

  if (q.isLoading || !q.data) return <div style={{ padding: 8, color: 'var(--mut)', fontSize: 12.5 }}>Loading…</div>
  const v = q.data
  const val = (k: keyof VendorDetail) => (k in draft ? draft[k] : v[k]) as string | null
  const set = (k: string, x: unknown) => setDraft((d) => ({ ...d, [k]: x }))
  const dirty = Object.keys(draft).length > 0
  const outOfPlay = (val('status') === 'hold' || val('status') === 'disqualified')

  const fld = (k: keyof VendorDetail, label: string, hint?: string) => (
    <div>
      <label style={{ margin: '0 0 3px' }}>{label}</label>
      <input className="si" style={{ width: '100%' }} value={val(k) ?? ''} onChange={(e) => set(k, e.target.value || null)} />
      {hint && <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 2 }}>{hint}</div>}
    </div>
  )

  return (
    <div style={{ padding: '8px 2px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <div style={{ fontSize: 12, color: 'var(--mut)' }}>
          {count(v.bid_count, 'bid')} on record · {count(v.award_count, 'award')}
        </div>
        <button className="btn pri sm" onClick={() => saveM.mutate()} disabled={!dirty || saveM.isPending}>
          {saveM.isPending ? 'Saving…' : dirty ? 'Save' : 'Saved'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {fld('name', 'Name')}
        {fld('code', 'Code')}
        <div>
          <label style={{ margin: '0 0 3px' }}>Role</label>
          <select className="si" style={{ width: '100%' }} value={val('role') ?? 'supplier'} onChange={(e) => set('role', e.target.value)}>
            {VENDOR_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label style={{ margin: '0 0 3px' }}>Status</label>
          <select className="si" style={{ width: '100%' }} value={val('status') ?? 'approved'} onChange={(e) => set('status', e.target.value)}>
            {VENDOR_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 10 }}>
        <div>
          <label style={{ margin: '0 0 3px' }}>Manufactures (OEMs)</label>
          <input className="si" style={{ width: '100%' }}
            value={(('oem_names' in draft ? draft.oem_names : v.oem_names) as string[] | null)?.join(', ') ?? ''}
            onChange={(e) => set('oem_names', e.target.value ? e.target.value.split(',').map((s) => s.trim()).filter(Boolean) : null)} />
          <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 2 }}>who actually builds it, if not them</div>
        </div>
        {fld('factory_country', 'Factory country', 'tariff exposure')}
        {fld('factory_location', 'Factory location')}
        {fld('integration_location', 'Integration location')}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, marginTop: 10 }}>
        {fld('sub_supplier', 'Sub-supplier')}
        {fld('notes', 'Notes')}
      </div>

      {outOfPlay && (
        <div style={{ marginTop: 10 }}>
          <label style={{ margin: '0 0 3px' }}>Why {val('status')} <span style={{ color: 'var(--red)' }}>*</span></label>
          <input className="si" style={{ width: '100%' }} value={val('status_note') ?? ''} onChange={(e) => set('status_note', e.target.value || null)}
            placeholder="stated reason — they won't appear in bid dropdowns" />
        </div>
      )}
      {saveM.isError && <div className="note">{String(saveM.error).replace(/^Error:\s*/, '')}</div>}

      <div style={{ marginTop: 14, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)' }}>Contacts</div>
      <div style={{ display: 'flex', gap: 8, margin: '6px 0 8px', flexWrap: 'wrap' }}>
        <input className="si" style={{ width: 150 }} placeholder="Name" value={cname} onChange={(e) => setCname(e.target.value)} />
        <input className="si" style={{ width: 140 }} placeholder="Title" value={ctitle} onChange={(e) => setCtitle(e.target.value)} />
        <input className="si" style={{ width: 200 }} placeholder="Email" value={cemail} onChange={(e) => setCemail(e.target.value)} />
        <button className="btn sm" onClick={() => addC.mutate()} disabled={!cname || addC.isPending}>Add contact</button>
      </div>
      {v.contacts.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No contacts yet.</div>}
      {v.contacts.length > 0 && (
        <table>
          <tbody>
            {v.contacts.map((c) => (
              <tr key={c.id}>
                <td><strong>{c.name}</strong></td>
                <td style={{ color: 'var(--mut)' }}>{c.title ?? '—'}</td>
                <td style={{ color: 'var(--mut)' }}>{c.email ?? '—'}</td>
                <td className="num"><button className="btn sm danger" onClick={() => delC.mutate(c.id)} disabled={delC.isPending}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

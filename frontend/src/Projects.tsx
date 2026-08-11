import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPatch, apiPost } from './services/api'
import { byCode, nest } from './lib/locations'
import { count } from './lib/format'
import type { CapacityCheck, Contact, Project, ProjectDetail, ProjectLocation } from './types/rom'

const REDUNDANCY = ['N', 'N+1', '2N', '2N+1']
const COOLING = ['air-cooled', 'liquid', 'hybrid']
const FUNCTIONS = ['procurement', 'electrical design', 'mechanical design', 'schedule', 'cost', 'program', 'commissioning']
const ACCOUNTABILITY = ['accountable', 'responsible', 'consulted', 'informed']

export default function ProjectsFace({ project, onPick }: { project: string; onPick: (n: string) => void }) {
  const qc = useQueryClient()
  const projectsQ = useQuery({ queryKey: ['projects'], queryFn: () => apiGet<Project[]>('/projects') })
  const projects = projectsQ.data ?? []
  const [name, setName] = useState('')
  const [thawReason, setThawReason] = useState('')
  const createM = useMutation({
    mutationFn: () => apiPost<Project>('/projects', { name }),
    onSuccess: (p) => { setName(''); onPick(p.name); qc.invalidateQueries({ queryKey: ['projects'] }) },
  })
  const selected = projects.find((p) => p.name === project)
  const frozen = selected?.legend_frozen ?? false
  const freezeM = useMutation({
    mutationFn: () => apiPost(`/projects/${selected?.id}/legend/freeze`, { reason: null, actor: 'web' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
  const thawM = useMutation({
    mutationFn: () => apiPost(`/projects/${selected?.id}/legend/thaw`, { reason: thawReason, actor: 'web' }),
    onSuccess: () => { setThawReason(''); qc.invalidateQueries({ queryKey: ['projects'] }) },
  })

  return (
    <div>
      <div className="headline"><h2>Projects</h2><span className="pill live">LIVE · Supabase</span></div>
      <p className="desc">Create a project, define its building / area codes, then freeze the legend so codes can't drift — codes stay in the project's crosswalk forever, and a thaw requires a stated reason.</p>
      <div className="two">
        <div className="card">
          <h4>① Create / pick project</h4>
          <label>New project name</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="fld" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Mitten" />
            <button className="btn pri" onClick={() => createM.mutate()} disabled={!name || createM.isPending}>Create</button>
          </div>
          <label style={{ marginTop: 14 }}>Existing</label>
          <div>
            {projects.length === 0 && <span style={{ color: 'var(--mut)', fontSize: 13 }}>none yet</span>}
            {projects.map((p) => (
              <button key={p.id} className="btn sm" style={{ marginRight: 6, marginBottom: 6, ...(p.name === project ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}) }} onClick={() => onPick(p.name)}>{p.name}{p.legend_frozen ? ' 🔒' : ''}</button>
            ))}
          </div>
        </div>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ margin: 0 }}>② Building / area codes {selected ? `· ${selected.name}` : ''}</h4>
            {selected && (frozen
              ? <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>🔒 legend frozen</span>
              : <button className="btn sm" onClick={() => freezeM.mutate()} disabled={freezeM.isPending}>Freeze legend</button>)}
          </div>
          {!selected ? <p style={{ color: 'var(--mut)', fontSize: 13, marginTop: 10 }}>Pick or create a project first.</p> : (
            <>
              {frozen && (
                <div className="note" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span>Frozen — a reason is required to change codes.</span>
                  <input className="si" style={{ flex: 1 }} placeholder="reason to thaw…" value={thawReason} onChange={(e) => setThawReason(e.target.value)} />
                  <button className="btn sm danger" onClick={() => thawM.mutate()} disabled={!thawReason || thawM.isPending}>Thaw</button>
                </div>
              )}
              <div style={{ marginTop: 10 }}><LocationEditor projectId={selected.id} frozen={frozen} /></div>
            </>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div style={{ marginTop: 16 }}><Detail project={selected} /></div>
          <div style={{ marginTop: 16 }}><Accountability projectId={selected.id} /></div>
        </>
      )}
    </div>
  )
}

/** What makes a project inferable: capacity, topology, jurisdiction, site conditions. */
function Detail({ project }: { project: Project }) {
  const qc = useQueryClient()
  const [draft, setDraft] = useState<Partial<ProjectDetail>>({})
  const value = <K extends keyof ProjectDetail>(k: K): ProjectDetail[K] =>
    (k in draft ? draft[k] : project[k]) as ProjectDetail[K]
  const set = <K extends keyof ProjectDetail>(k: K, v: ProjectDetail[K]) =>
    setDraft((d) => ({ ...d, [k]: v }))
  const dirty = Object.keys(draft).length > 0

  const capQ = useQuery({
    queryKey: ['capacity', project.id],
    queryFn: () => apiGet<CapacityCheck>(`/projects/${project.id}/capacity`),
  })
  const saveM = useMutation({
    mutationFn: () => apiPatch<Project>(`/projects/${project.id}`, draft),
    onSuccess: () => {
      setDraft({})
      qc.invalidateQueries({ queryKey: ['projects'] })
      qc.invalidateQueries({ queryKey: ['capacity', project.id] })
    },
  })

  const txt = (k: keyof ProjectDetail, label: string, hint?: string, w = 1) => (
    <div style={{ gridColumn: `span ${w}` }}>
      <label style={{ margin: '0 0 3px' }}>{label}</label>
      <input className="fld" value={(value(k) as string | null) ?? ''} onChange={(e) => set(k, (e.target.value || null) as never)} />
      {hint && <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 2 }}>{hint}</div>}
    </div>
  )
  const num = (k: keyof ProjectDetail, label: string, hint?: string) => (
    <div>
      <label style={{ margin: '0 0 3px' }}>{label}</label>
      <input className="fld" type="number" value={(value(k) as number | null) ?? ''} onChange={(e) => set(k, (e.target.value === '' ? null : Number(e.target.value)) as never)} />
      {hint && <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 2 }}>{hint}</div>}
    </div>
  )
  const pick = (k: keyof ProjectDetail, label: string, options: string[], hint?: string) => (
    <div>
      <label style={{ margin: '0 0 3px' }}>{label}</label>
      <select className="fld" value={(value(k) as string | null) ?? ''} onChange={(e) => set(k, (e.target.value || null) as never)}>
        <option value="">—</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      {hint && <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 2 }}>{hint}</div>}
    </div>
  )
  const cap = capQ.data
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
        <h4 style={{ margin: 0 }}>③ Project detail · {project.name}</h4>
        <button className="btn pri sm" onClick={() => saveM.mutate()} disabled={!dirty || saveM.isPending}>
          {saveM.isPending ? 'Saving…' : dirty ? `Save ${count(Object.keys(draft).length, 'change')}` : 'Saved'}
        </button>
      </div>
      <p style={{ fontSize: 12, color: 'var(--mut)', margin: '4px 0 12px' }}>
        These aren't paperwork — they're what let history be inferred onto this project. Capacity and
        redundancy are the denominators for quantity; jurisdiction drives tax and freight; the site
        conditions are what qualified and disqualified real bids.
      </p>

      <Sub>Identity &amp; title</Sub>
      <G>
        {txt('site_code', 'Site code', 'e.g. DTW01')}
        {txt('buyer_entity', 'Buyer legal entity', 'legal name of the company assigned to this project', 3)}
      </G>
      <G>
        {txt('address', 'Address', undefined, 2)}
        {txt('city', 'City')}
        {txt('state', 'State / region', 'drives tax jurisdiction')}
      </G>
      <G>{txt('country', 'Country', 'country of the site, not of origin')}</G>

      <div style={{ marginTop: 12 }}><Sub>Capacity &amp; topology</Sub></div>
      <G>
        {num('mw_it', 'MW IT (total)', 'the project denominator — $/MW and units/MW')}
        {pick('redundancy', 'Redundancy', REDUNDANCY, '2N doubles the electrical count')}
        {pick('cooling', 'Cooling', COOLING, 'changes the equipment list outright')}
      </G>
      <div style={{ fontSize: 11, color: '#9aa0a6', marginTop: -2, marginBottom: 4 }}>
        No energization date here — that's a schedule output, and the schedule owns it. What the record
        needs is each unit's <strong>required-by</strong> date, captured on the Design register.
      </div>
      <BuildingCapacity projectId={project.id} projectMw={value('mw_it') as number | null} />
      {cap && (
        <div className="note" style={{ marginTop: 4 }}>
          {cap.buildings_total === 0
            ? 'No buildings yet — add codes above, then give each its MW so quantity inference has something to divide by.'
            : cap.reconciles
              ? <>Buildings account for all {cap.building_mw_it} MW.</>
              : <>
                  {cap.buildings_with_capacity} of {count(cap.buildings_total, 'building')} state a capacity, totalling{' '}
                  <strong>{cap.building_mw_it} MW</strong>
                  {cap.project_mw_it != null && <> against the project's <strong>{cap.project_mw_it} MW</strong></>}.
                  {' '}A gap here makes every units-per-MW inference wrong.
                </>}
        </div>
      )}

      <div style={{ marginTop: 12 }}><Sub>Site conditions</Sub></div>
      <G>
        {num('elevation_ft', 'Elevation (ft)', 'derates equipment; bids are rated to it')}
        {num('ambient_max_f', 'Ambient design max (°F)', 'kW/ton is quoted at this temperature')}
        {num('sound_limit_dba', 'Sound limit (dBA)', 'drove $35k–$60k enclosure adders')}
      </G>
      {saveM.isError && <div className="note">{String(saveM.error).replace(/^Error:\s*/, '')}</div>}
    </div>
  )
}

/**
 * MW per building, assigned where the total and the reconciliation are — so the gap and the
 * fix are in the same place. Buildings only: capacity rolls up at the building, and areas
 * inherit it rather than splitting it again.
 */
function BuildingCapacity({ projectId, projectMw }: { projectId: string; projectMw: number | null }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['locations', projectId], queryFn: () => apiGet<ProjectLocation[]>(`/projects/${projectId}/locations`) })
  const buildings = (q.data ?? []).filter((l) => l.kind === 'building').sort(byCode)
  const [edits, setEdits] = useState<Record<string, number | ''>>({})
  const saveM = useMutation({
    mutationFn: ({ id, mw }: { id: string; mw: number | null }) =>
      apiPatch(`/projects/${projectId}/locations/${id}`, { mw_it: mw }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['locations', projectId] })
      qc.invalidateQueries({ queryKey: ['capacity', projectId] })
    },
  })
  const shown = (b: ProjectLocation) => (b.id in edits ? edits[b.id] : (b.mw_it ?? ''))
  const commit = (b: ProjectLocation) => {
    const v = shown(b)
    const next = v === '' ? null : Number(v)
    if (next !== (b.mw_it ?? null)) saveM.mutate({ id: b.id, mw: next })
  }
  const assigned = buildings.reduce((n, b) => n + Number(shown(b) || 0), 0)
  const remainder = projectMw == null ? null : Math.round((projectMw - assigned) * 1000) / 1000

  if (buildings.length === 0) return null
  return (
    <div style={{ marginTop: 4, marginBottom: 6 }}>
      <label style={{ margin: '0 0 5px' }}>MW IT per building</label>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        {buildings.map((b) => (
          <div key={b.id} style={{ width: 108 }}>
            <div style={{ fontSize: 11, color: 'var(--mut)', marginBottom: 2 }}>
              <strong style={{ color: 'var(--ink)' }}>{b.code}</strong>{b.label ? ` · ${b.label}` : ''}
            </div>
            <input className="si" style={{ width: '100%' }} type="number" placeholder="MW"
              value={shown(b)}
              onChange={(e) => setEdits((d) => ({ ...d, [b.id]: e.target.value === '' ? '' : Number(e.target.value) }))}
              onBlur={() => commit(b)} />
          </div>
        ))}
        <div style={{ fontSize: 12, color: 'var(--mut)', paddingBottom: 7 }}>
          assigned <strong style={{ color: 'var(--ink)' }}>{assigned}</strong>
          {remainder != null && remainder !== 0 && (
            <span style={{ color: remainder > 0 ? 'var(--amber)' : 'var(--red)' }}>
              {' '}· {remainder > 0 ? `${remainder} MW unassigned` : `${-remainder} MW over`}
            </span>
          )}
          {remainder === 0 && <span style={{ color: 'var(--accent)' }}> · balanced</span>}
        </div>
      </div>
      {saveM.isError && <div className="note">{String(saveM.error).replace(/^Error:\s*/, '')}</div>}
    </div>
  )
}

/** Who is accountable and responsible, by function. Recorded, not enforced. */
function Accountability({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['contacts', projectId], queryFn: () => apiGet<Contact[]>(`/projects/${projectId}/contacts`) })
  const contacts = q.data ?? []
  const [name, setName] = useState('')
  const [fn, setFn] = useState(FUNCTIONS[0])
  const [acc, setAcc] = useState('responsible')
  const [org, setOrg] = useState('')
  const [email, setEmail] = useState('')
  const invalidate = () => qc.invalidateQueries({ queryKey: ['contacts', projectId] })
  const addM = useMutation({
    mutationFn: () => apiPost(`/projects/${projectId}/contacts`, { name, function: fn, accountability: acc, org: org || null, email: email || null }),
    onSuccess: () => { setName(''); setOrg(''); setEmail(''); invalidate() },
  })
  const delM = useMutation({ mutationFn: (id: string) => apiDelete(`/projects/${projectId}/contacts/${id}`), onSuccess: invalidate })

  const missing = FUNCTIONS.filter((f) => !contacts.some((c) => c.function === f && c.accountability === 'accountable'))
  return (
    <div className="card">
      <h4 style={{ margin: 0 }}>④ Accountable &amp; responsible</h4>
      <p style={{ fontSize: 12, color: 'var(--mut)', margin: '4px 0 12px' }}>
        One accountable person per function, and whoever else is responsible. Recorded, not enforced —
        there's no user model behind this yet, so it's a signature ledger rather than a permission system.
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 10 }}>
        <div style={{ width: 160 }}><label style={{ margin: '0 0 3px' }}>Name</label><input className="si" style={{ width: '100%' }} value={name} onChange={(e) => setName(e.target.value)} /></div>
        <div style={{ width: 160 }}><label style={{ margin: '0 0 3px' }}>Function</label><select className="si" style={{ width: '100%' }} value={fn} onChange={(e) => setFn(e.target.value)}>{FUNCTIONS.map((f) => <option key={f} value={f}>{f}</option>)}</select></div>
        <div style={{ width: 130 }}><label style={{ margin: '0 0 3px' }}>Role</label><select className="si" style={{ width: '100%' }} value={acc} onChange={(e) => setAcc(e.target.value)}>{ACCOUNTABILITY.map((a) => <option key={a} value={a}>{a}</option>)}</select></div>
        <div style={{ width: 130 }}><label style={{ margin: '0 0 3px' }}>Org</label><input className="si" style={{ width: '100%' }} value={org} onChange={(e) => setOrg(e.target.value)} /></div>
        <div style={{ width: 190 }}><label style={{ margin: '0 0 3px' }}>Email</label><input className="si" style={{ width: '100%' }} value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }} onClick={() => addM.mutate()} disabled={!name || addM.isPending}>Add</button>
      </div>
      {contacts.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>Nobody assigned yet.</div>}
      {contacts.length > 0 && (
        <table>
          <thead><tr><th>Function</th><th>Name</th><th>Role</th><th>Org</th><th>Email</th><th /></tr></thead>
          <tbody>
            {contacts.map((c) => (
              <tr key={c.id}>
                <td>{c.function}</td>
                <td><strong>{c.name}</strong></td>
                <td><span style={{ color: c.accountability === 'accountable' ? 'var(--accent)' : 'var(--mut)', fontWeight: c.accountability === 'accountable' ? 600 : 400 }}>{c.accountability}</span></td>
                <td style={{ color: 'var(--mut)' }}>{c.org ?? '—'}</td>
                <td style={{ color: 'var(--mut)' }}>{c.email ?? '—'}</td>
                <td className="num"><button className="btn sm danger" onClick={() => delM.mutate(c.id)} disabled={delM.isPending}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {missing.length > 0 && (
        <div className="note">No one accountable for: {missing.join(' · ')}.</div>
      )}
      {addM.isError && <div className="note">{String(addM.error).replace(/^Error:\s*/, '')}</div>}
    </div>
  )
}

/** A row of fields. Must live at module scope: a component defined inside another gets a
 *  fresh type identity on every render, which remounts its subtree and drops focus. */
function G({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 4 }}>{children}</div>
}

function Sub({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)', marginBottom: 6 }}>{children}</div>
}

function LocationEditor({ projectId, frozen }: { projectId: string; frozen: boolean }) {
  const qc = useQueryClient()
  const locQ = useQuery({ queryKey: ['locations', projectId], queryFn: () => apiGet<ProjectLocation[]>(`/projects/${projectId}/locations`) })
  const locs = locQ.data ?? []
  const invalidate = () => qc.invalidateQueries({ queryKey: ['locations', projectId] })
  const [code, setCode] = useState('')
  const [kind, setKind] = useState('building')
  const [labelText, setLabelText] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editCode, setEditCode] = useState('')
  const [editLabel, setEditLabel] = useState('')
  const addM = useMutation({ mutationFn: () => apiPost(`/projects/${projectId}/locations`, { code, kind, label: labelText || null }), onSuccess: () => { setCode(''); setLabelText(''); invalidate() } })
  const updateM = useMutation({ mutationFn: (id: string) => apiPatch(`/projects/${projectId}/locations/${id}`, { code: editCode, label: editLabel || null }), onSuccess: () => { setEditingId(null); invalidate() } })
  const deleteM = useMutation({ mutationFn: (id: string) => apiDelete(`/projects/${projectId}/locations/${id}`), onSuccess: invalidate })
  const startEdit = (l: ProjectLocation) => { setEditingId(l.id); setEditCode(l.code); setEditLabel(l.label ?? '') }

  const { buildings, areas, parentOf, orphans } = nest(locs)

  const row = (l: ProjectLocation, indent: number) => editingId === l.id ? (
    <div style={{ display: 'flex', gap: 6, marginLeft: indent, alignItems: 'center', padding: '2px 0' }}>
      <input className="si" style={{ width: 90 }} value={editCode} onChange={(e) => setEditCode(e.target.value)} />
      <input className="si" style={{ width: 130 }} value={editLabel} onChange={(e) => setEditLabel(e.target.value)} placeholder="label" />
      <button className="btn sm" onClick={() => updateM.mutate(l.id)} disabled={updateM.isPending}>Save</button>
      <button className="btn sm" onClick={() => setEditingId(null)}>Cancel</button>
    </div>
  ) : (
    <div style={{ marginLeft: indent, display: 'flex', gap: 8, alignItems: 'baseline', padding: '2px 0' }}>
      <span>{indent ? '↳ ' : ''}<strong>{l.code}</strong> <span style={{ color: 'var(--mut)' }}>{l.kind}{l.label ? ` · ${l.label}` : ''}{l.mw_it != null ? ` · ${l.mw_it} MW` : ''}</span></span>
      {!frozen && <button className="btn sm" onClick={() => startEdit(l)}>edit</button>}
      {!frozen && <button className="btn sm danger" onClick={() => deleteM.mutate(l.id)} disabled={deleteM.isPending}>✕</button>}
    </div>
  )

  return (
    <div>
      {!frozen && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          <input className="si" style={{ width: 90 }} placeholder="code (C1)" value={code} onChange={(e) => setCode(e.target.value)} />
          <select className="si" value={kind} onChange={(e) => setKind(e.target.value)}><option value="building">building</option><option value="area">area</option></select>
          <input className="si" style={{ width: 140 }} placeholder="label (Compute 1)" value={labelText} onChange={(e) => setLabelText(e.target.value)} />
          <button className="btn sm" style={{ background: 'var(--ink)', color: '#fff', borderColor: 'var(--ink)' }} onClick={() => addM.mutate()} disabled={!code || addM.isPending}>Add</button>
        </div>
      )}
      {locs.length === 0 && <div style={{ color: 'var(--mut)', fontSize: 12.5 }}>No codes yet.</div>}
      {locs.length > 0 && (
        <div style={{ fontSize: 13 }}>
          {[...buildings].sort(byCode).map((b) => (
            <div key={b.id} style={{ marginBottom: 4 }}>
              {row(b, 0)}
              {areas.filter((a) => parentOf(a)?.id === b.id).sort(byCode).map((a) => <div key={a.id}>{row(a, 16)}</div>)}
            </div>
          ))}
          {orphans.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <span style={{ color: 'var(--mut)', fontStyle: 'italic' }}>unassigned areas (no matching building code)</span>
              {[...orphans].sort(byCode).map((a) => <div key={a.id}>{row(a, 16)}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

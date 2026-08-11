import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiPatch, apiPost } from './services/api'
import RomGrid from './RomGrid'
import SourcingFace from './Sourcing'
import { STATE, TIER, count, describe, money } from './lib/format'
import { resolveSpec, subTypesFor, unitTypeCodes } from './lib/equipment'
import { byCode, locationOptions, nest } from './lib/locations'
import type { DemandLineRow, EquipmentType, FreezeScopePreview, Project, ProjectLocation, RomBand, RomPriceRequest } from './types/rom'

const STOPS = [
  ['DEMAND', 1], ['SOURCING', 1], ['AGREEMENT', 0], ['PRODUCTION', 0],
  ['CUSTODY', 0], ['HANDOVER', 0], ['OPERATION', 0], ['DISPOSITION', 0],
] as const
const TABS = [
  { k: 'projects', label: 'Projects', live: true },
  { k: 'demand', label: 'Demand', live: true },
  { k: 'sourcing', label: 'Sourcing', live: true },
  { k: 'cost', label: 'Cost' }, { k: 'logistics', label: 'Logistics' },
  { k: 'vendor', label: 'Vendor' }, { k: 'ops', label: 'Operations' },
  { k: 'disposition', label: 'Disposition' }, { k: 'program', label: 'Program' },
]

export default function App() {
  const [project, setProject] = useState('DEMO')
  const [tab, setTab] = useState('demand')
  const projectsQ = useQuery({ queryKey: ['projects'], queryFn: () => apiGet<Project[]>('/projects') })
  const projects = projectsQ.data ?? []
  const projectNames = [...new Set([project, ...projects.map((p) => p.name)])]
  return (
    <div className="wrap">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Viasel</h1>
        <div style={{ fontSize: 12, color: 'var(--mut)', display: 'flex', gap: 6, alignItems: 'center' }}>
          Project
          <select className="si" value={project} onChange={(e) => setProject(e.target.value)}>
            {projectNames.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <span style={{ color: '#9aa0a6' }}>· create in Projects tab</span>
        </div>
      </div>
      <p className="sub">One record per unit — priced from history, frozen, sourced, awarded.</p>

      <div className="road">
        {STOPS.map(([name, done]) => <div key={name} className={`stop${done ? ' here' : ''}`}><span className="dot" /><b>{name}</b></div>)}
      </div>
      <p className="roadnote">Each unit travels this road. The green stops are live; the rest are the roadmap.</p>

      <div className="tabs">
        {TABS.map((t) => <div key={t.k} className={`tab${tab === t.k ? ' active' : ''}`} onClick={() => setTab(t.k)}>{t.live && <span className="star">★</span>}{t.label}</div>)}
      </div>

      {tab === 'projects' && <ProjectsFace project={project} onPick={setProject} />}
      {tab === 'demand' && <DemandFace project={project} projectId={projects.find((p) => p.name === project)?.id} />}
      {tab === 'sourcing' && <SourcingFace project={project} />}
      {tab === 'cost' && <Preview title="Cost / Finance — Reconciliation" phase="Phase 2 · the wedge" body="Committed vs. actual and exposure compute themselves and drill to the unit." mock="[ committed-vs-actual by cost code · every row drills to a unit ]" note="Catches the $1.279M gap across 52 executed POs/COs that took weeks to find by hand." />}
      {tab === 'logistics' && <Preview title="Logistics / Custody" phase="Phase 3" body="Every unit's location — factory · transit · warehouse · staged · installed — with exceptions flagged." mock="[ where-is-everything board · phone scan: receive · condition · zone ]" />}
      {tab === 'vendor' && <Preview title="Vendor portal" phase="later" body="Report production stage, upload test reports & serials, mark shipped." mock="[ your scope · report status ]" note="Submitting = getting paid faster; ends four people chasing status." />}
      {tab === 'ops' && <Preview title="Operations — Live Health" phase="Phase 4" body="Each unit green/yellow/red vs. its own day-zero baseline; one plain-English digest a day." mock="[ fleet health · '3 units drifting — UPS-07 battery trending warm' ]" />}
      {tab === 'disposition' && <Preview title="Disposition — the passport" phase="Phase 4" body="Scan a unit → its whole life on one page. Transfer hands the record to the next owner." mock="[ biography: spec · price · changes · storage · service · health ]" />}
      {tab === 'program' && <Preview title="Program — the rollup" phase="later" body="Across projects: covered · pending procurement · at risk · surplus vs. shortfall — every number drills to a line." mock="[ demand fulfillment by freeze set · net change by type ]" />}
    </div>
  )
}

function Preview({ title, phase, body, mock, note }: { title: string; phase: string; body: string; mock: string; note?: string }) {
  return (
    <div>
      <div className="headline"><h2>{title}</h2><span className="pill">{phase}</span></div>
      <p className="desc">{body}</p>
      <div className="card"><div className="ph">{mock}</div>{note && <div className="note">{note}</div>}</div>
    </div>
  )
}

function ProjectsFace({ project, onPick }: { project: string; onPick: (n: string) => void }) {
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
    </div>
  )
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
      <span>{indent ? '↳ ' : ''}<strong>{l.code}</strong> <span style={{ color: 'var(--mut)' }}>{l.kind}{l.label ? ` · ${l.label}` : ''}</span></span>
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

function DemandFace({ project, projectId }: { project: string; projectId?: string }) {
  const [mode, setMode] = useState<'grid' | 'quick'>('grid')
  return (
    <div>
      <div className="headline"><h2>Demand Management — Design &amp; ROM</h2><span className="pill live">LIVE · Supabase</span></div>
      <p className="desc">Price requirements from executed history, save them as demand, freeze them. No sourcing here — frozen demand flows to the Sourcing face.</p>

      <div className="seg" style={{ marginBottom: 12 }}>
        <button className={mode === 'grid' ? 'on' : ''} onClick={() => setMode('grid')}>Line-item list</button>
        <button className={mode === 'quick' ? 'on' : ''} onClick={() => setMode('quick')}>Quick price</button>
      </div>
      <p className="desc" style={{ marginTop: -6 }}>
        {mode === 'grid'
          ? 'Stack the whole scope — type · size · qty · location — and ROM the list in one pass into a work-in-progress project ROM.'
          : 'One requirement, one band, with the full layer breakdown. Same engine, same history.'}
      </p>

      {mode === 'grid' ? <RomGrid project={project} projectId={projectId} /> : <QuickPrice project={project} projectId={projectId} />}

      <div style={{ marginTop: 16 }}><DemandBoard project={project} projectId={projectId} /></div>
    </div>
  )
}

function QuickPrice({ project, projectId }: { project: string; projectId?: string }) {
  const qc = useQueryClient()
  const typesQ = useQuery({ queryKey: ['equipment-types'], queryFn: () => apiGet<EquipmentType[]>('/equipment-types') })
  const types = typesQ.data ?? []
  const unitCodes = unitTypeCodes(types)

  const [type, setType] = useState('Padmount Transformer')
  const [sub, setSub] = useState('')
  const [qty, setQty] = useState(12)
  const [locId, setLocId] = useState('')
  const subs = subTypesFor(types, type)
  const { row, subType: effSub, size, denominator: denom } = resolveSpec(types, type, sub)

  const locQ = useQuery({
    queryKey: ['locations', projectId],
    queryFn: () => apiGet<ProjectLocation[]>(`/projects/${projectId}/locations`),
    enabled: !!projectId,
  })
  const locOpts = locationOptions(locQ.data ?? [])
  const loc = locOpts.find((o) => o.id === locId)

  const priceM = useMutation({ mutationFn: (r: RomPriceRequest) => apiPost<RomBand>('/rom/price', r) })
  const band = priceM.data
  const saveM = useMutation({
    mutationFn: () => apiPost<DemandLineRow>('/demand-lines', {
      project_id: project, qty: Number(qty), equipment_type_id: row?.id ?? null,
      spec_attributes: { type_query: type, denominator: denom, size, sub: effSub },
      target_building: loc?.building ?? null, target_area: loc?.area ?? null,
      rom_unit_price: band?.unit_mid ?? null, rom_confidence: band?.confidence_tier ?? null, rom_comparables_count: band?.comparables_count ?? null,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['demand-lines'] }),
  })

  return (
    <div className="two">
      <div className="card">
        <h4>① Requirement</h4>
        <label>Equipment type</label>
        <select className="fld" value={type} onChange={(e) => { setType(e.target.value); setSub('') }} disabled={typesQ.isLoading}>
          {typesQ.isLoading && <option>loading…</option>}
          {unitCodes.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <label>Size / configuration</label>
        <select className="fld" value={effSub} onChange={(e) => setSub(e.target.value)} disabled={subs.length === 0}>
          {subs.length === 0 && <option value="">— none on record —</option>}
          {subs.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label>Quantity</label>
        <input className="fld" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
        <label>Location</label>
        <select className="fld" value={locId} onChange={(e) => setLocId(e.target.value)} disabled={locOpts.length === 0}>
          <option value="">{locOpts.length === 0 ? '— no codes for this project yet —' : '— unassigned —'}</option>
          {locOpts.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </select>
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--mut)', display: 'flex', gap: 14 }}>
          <span>size <strong className="chip">{size}</strong></span><span>denominator <strong className="chip">{denom}</strong></span>
        </div>
        <div style={{ fontSize: 11, color: '#9aa0a6', marginTop: 4 }}>size &amp; denominator come from the equipment — not typed</div>
        <button className="btn pri" style={{ marginTop: 14, width: '100%' }} onClick={() => priceM.mutate({ type_query: type, denominator: denom, size, qty: Number(qty) })} disabled={priceM.isPending}>{priceM.isPending ? 'Pricing…' : 'Price it'}</button>
      </div>

      <div className="card">
        <h4>② Price band — a byproduct of your history</h4>
        {priceM.isError && <p style={{ color: 'var(--red)' }}>Couldn’t reach the API (backend on :8000, key set?).</p>}
        {!band && !priceM.isError && <p style={{ color: 'var(--mut)' }}>Pick a type and hit “Price it”.</p>}
        {band && (
          <div className="band">
            <div className="nums"><span>{money(band.unit_low)}</span><span className="mid">{money(band.unit_mid)}</span><span>{money(band.unit_high)}</span></div>
            <div className="track" />
            <div style={{ fontSize: 12, color: 'var(--mut)' }}>per unit ({band.denominator}) · extended <strong>{money(band.extended_mid)}</strong> (×{band.qty})</div>
            <div style={{ marginTop: 10, fontSize: 13 }}>Confidence: <strong style={{ color: TIER[band.confidence_tier] }}>{band.confidence_tier}</strong> · {band.comparables_count} comparables</div>
            {band.note && <div className="note">{band.note}</div>}
            <button className="btn" style={{ marginTop: 12, width: '100%', borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => saveM.mutate()} disabled={saveM.isPending || band.unit_mid == null}>{saveM.isPending ? 'Saving…' : 'Save as demand line ▸'}</button>
          </div>
        )}
      </div>
    </div>
  )
}

function DemandBoard({ project, projectId }: { project: string; projectId?: string }) {
  const qc = useQueryClient()
  const [scope, setScope] = useState('project')
  const [scopeRef, setScopeRef] = useState('')
  const q = useQuery({ queryKey: ['demand-lines', project], queryFn: () => apiGet<DemandLineRow[]>(`/demand-lines?project=${project}`) })
  const lines = q.data ?? []
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['demand-lines'] })
    qc.invalidateQueries({ queryKey: ['freeze-preview'] })
    qc.invalidateQueries({ queryKey: ['candidates', project] })
  }

  // the project's own codes are the scope axis — a building freeze picks a real building
  const locQ = useQuery({
    queryKey: ['locations', projectId],
    queryFn: () => apiGet<ProjectLocation[]>(`/projects/${projectId}/locations`),
    enabled: !!projectId,
  })
  const locs = locQ.data ?? []
  const refOptions = scope === 'building'
    ? locs.filter((l) => l.kind === 'building')
    : scope === 'area' ? locs.filter((l) => l.kind === 'area') : []
  const needsRef = scope !== 'project'
  const ref = needsRef ? (refOptions.some((o) => o.code === scopeRef) ? scopeRef : refOptions[0]?.code ?? '') : ''

  // what this scope would lock, resolved server-side — the same query the freeze runs
  const previewQ = useQuery({
    queryKey: ['freeze-preview', project, scope, ref],
    queryFn: () => apiGet<FreezeScopePreview>(
      `/freeze/preview?project=${encodeURIComponent(project)}&scope=${scope}` +
      (ref ? `&scope_ref=${encodeURIComponent(ref)}` : '')),
    enabled: !needsRef || !!ref,
  })
  const preview = previewQ.data

  const freezeM = useMutation({
    mutationFn: () => apiPost('/freeze', { project_id: project, scope, scope_ref: ref || null, actor: 'web' }),
    onSuccess: invalidate,
  })
  const thawM = useMutation({ mutationFn: (id: string) => apiPost(`/demand-lines/${id}/thaw`, { reason: null }), onSuccess: invalidate })
  const covered = new Set(preview?.demand_line_ids ?? [])

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0 }}>③ Demand board</h4>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--mut)' }}>freeze the</span>
          <select className="si" value={scope} onChange={(e) => { setScope(e.target.value); setScopeRef('') }} title="how much of the design this freeze locks — design releases by place">
            <option value="project">whole project</option>
            <option value="building">building</option>
            <option value="area">area / hall</option>
          </select>
          {needsRef && (
            refOptions.length === 0
              ? <span style={{ fontSize: 11, color: 'var(--red)' }}>no {scope} codes — add them in Projects</span>
              : <select className="si" value={ref} onChange={(e) => setScopeRef(e.target.value)}>
                  {refOptions.map((o) => <option key={o.id} value={o.code}>{o.code}{o.label ? ` · ${o.label}` : ''}</option>)}
                </select>
          )}
          <button className="btn pri sm" onClick={() => freezeM.mutate()} disabled={!preview || preview.line_count === 0 || freezeM.isPending}>
            {freezeM.isPending ? 'Freezing…' : `Freeze ${preview ? count(preview.line_count, 'line') : '…'} ▸`}
          </button>
        </div>
      </div>
      {preview && (
        <div style={{ fontSize: 12, color: preview.line_count === 0 ? 'var(--mut)' : 'var(--ink)', margin: '6px 0 2px' }}>
          {preview.line_count === 0
            ? <>Nothing drafted in {scope === 'project' ? 'this project' : `${scope} ${ref}`} to freeze.</>
            : <>This locks <strong>{count(preview.line_count, 'line')}</strong> · {count(preview.total_qty, 'unit')}
                {preview.rom_extended != null && <> · {money(preview.rom_extended)} at ROM</>}
                <span style={{ color: 'var(--mut)' }}> — the scope decides, not a hand-picked list.</span></>}
        </div>
      )}
      {freezeM.isError && <div className="note">{String(freezeM.error).replace(/^Error:\s*/, '')}</div>}
      {lines.length === 0 && <p style={{ color: 'var(--mut)', fontSize: 13 }}>No demand yet — price a requirement and save it.</p>}
      {lines.length > 0 && (
        <table style={{ marginTop: 8 }}>
          <thead><tr><th style={{ width: 26 }} /><th>Requirement</th><th>Building</th><th className="num">Qty</th><th className="num">ROM / unit</th><th>Status</th><th /></tr></thead>
          <tbody>
            {lines.map((d) => (
              <tr key={d.id}>
                <td title={covered.has(d.id) ? 'in the current freeze scope' : undefined}>
                  {d.state === 'drafted' && (covered.has(d.id)
                    ? <span style={{ color: 'var(--accent)', fontWeight: 700 }}>•</span>
                    : <span style={{ color: 'var(--line)' }}>·</span>)}
                </td>
                <td>{describe(d) || '—'}</td>
                <td>{d.target_building ?? '—'}{d.target_area ? ` · ${d.target_area}` : ''}</td>
                <td className="num">{d.qty}</td>
                <td className="num">{money(d.rom_unit_price)}</td>
                <td><span className="st" style={{ background: STATE[d.state] ?? '#6b7280' }}>{d.state}</span></td>
                <td className="num">{(d.state === 'frozen' || d.state === 'matched') && <button className="btn sm danger" onClick={() => thawM.mutate(d.id)} disabled={thawM.isPending}>Thaw</button>}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--mut)' }}>
                Board total · {lines.length} lines
              </td>
              <td className="num"><strong>{lines.reduce((n, d) => n + d.qty, 0)}</strong></td>
              <td className="num" colSpan={3} style={{ fontVariantNumeric: 'tabular-nums' }}>
                <strong>{money(lines.reduce((n, d) => n + (d.rom_unit_price ?? 0) * d.qty, 0))}</strong>
                <span style={{ color: 'var(--mut)', fontWeight: 400, fontSize: 11 }}> extended at ROM</span>
              </td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  )
}

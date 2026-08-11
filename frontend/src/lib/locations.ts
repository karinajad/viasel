import type { ProjectLocation } from '../types/rom'

export interface Nested {
  buildings: ProjectLocation[]
  areas: ProjectLocation[]
  parentOf: (a: ProjectLocation) => ProjectLocation | undefined
  orphans: ProjectLocation[]
}

/** Areas nest under the building whose code is the leading match (longest wins). */
export function nest(locs: ProjectLocation[]): Nested {
  const buildings = locs.filter((l) => l.kind === 'building').sort((a, b) => b.code.length - a.code.length)
  const areas = locs.filter((l) => l.kind === 'area')
  const parentOf = (a: ProjectLocation) => buildings.find((b) => a.code === b.code || a.code.startsWith(b.code))
  return { buildings, areas, parentOf, orphans: areas.filter((a) => !parentOf(a)) }
}

export const byCode = (a: ProjectLocation, b: ProjectLocation): number => a.code.localeCompare(b.code)

export interface LocationOption {
  id: string
  label: string
  building: string | null
  area: string | null
}

/**
 * One flat option list for a row's Location ▾ — buildings with their areas indented under
 * them. Picking an area carries its building along, so a demand line always lands in both.
 */
export function locationOptions(locs: ProjectLocation[]): LocationOption[] {
  const { buildings, areas, parentOf, orphans } = nest(locs)
  const out: LocationOption[] = []
  for (const b of [...buildings].sort(byCode)) {
    out.push({ id: b.id, label: b.label ? `${b.code} · ${b.label}` : b.code, building: b.code, area: null })
    for (const a of areas.filter((x) => parentOf(x)?.id === b.id).sort(byCode)) {
      out.push({ id: a.id, label: `  ↳ ${a.code}${a.label ? ` · ${a.label}` : ''}`, building: b.code, area: a.code })
    }
  }
  for (const a of [...orphans].sort(byCode)) {
    out.push({ id: a.id, label: `${a.code} (unassigned)`, building: null, area: a.code })
  }
  return out
}

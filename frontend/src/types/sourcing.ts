export interface CandidateGroup {
  type_query: string
  denominator: string
  size: number
  line_count: number
  total_qty: number
  rom_extended: number | null
  buildings: string[]
  demand_line_ids: string[]
}

export interface CandidatesRead {
  project_id: string
  groups: CandidateGroup[]
  unpoolable_count: number
}

export interface PackageLineRead {
  demand_line_id: string
  qty: number
  target_building: string | null
  target_area: string | null
  state: string
  rom_unit_price: number | null
}

/** One bid, on the same footing as every other bid on the lot. */
export interface LevelingRow {
  quote_id: string
  vendor: string
  oem: string | null
  unit_price: number
  effective_unit: number
  layers: Record<string, number>
  normalized: number
  lead_time_weeks: number | null
  terms_note: string | null
  state: string
  disposition_reason: string | null
  extended: number
  delta_vs_low: number
  delta_vs_low_pct: number | null
  delta_vs_rom: number | null
  delta_vs_rom_pct: number | null
  is_low: boolean
  is_selected: boolean
}

export interface PackageRead {
  id: string
  code: string
  project_id: string
  type_query: string
  denominator: string
  size: number
  state: string
  created_at: string
  line_count: number
  total_qty: number
  rom_unit_price: number | null
  rom_extended: number | null
  quote_count: number
  declined_count: number
  awarded_vendor: string | null
  awarded_extended: number | null
}

export interface PackageDetail {
  package: PackageRead
  lines: PackageLineRead[]
  leveling: LevelingRow[]
}

/** The facts that let history be inferred onto a project. All optional. */
export interface ProjectDetail {
  site_code: string | null
  buyer_entity: string | null
  address: string | null
  city: string | null
  state: string | null
  country: string | null
  mw_it: number | null
  redundancy: string | null
  cooling: string | null
  elevation_ft: number | null
  ambient_max_f: number | null
  sound_limit_dba: number | null
}

export interface Project extends ProjectDetail {
  id: string
  name: string
  legend_frozen: boolean
}

export interface Contact {
  id: string
  name: string
  function: string
  accountability: string
  org: string | null
  email: string | null
}

export interface CapacityCheck {
  project_mw_it: number | null
  building_mw_it: number
  buildings_with_capacity: number
  buildings_total: number
  reconciles: boolean
}

export interface ProjectLocation {
  id: string
  code: string
  kind: string
  label: string | null
  mw_it: number | null
}

export interface EquipmentType {
  id: string
  design_term: string
  unit_type_code: string
  sub_type: string | null
  natural_denominator: string
}

export interface DemandLineRow {
  id: string
  project_id: string
  qty: number
  state: string
  rom_unit_price: number | null
  rom_confidence: string | null
  /** which point of the band was taken, and why — set on the ROM face, not at capture */
  rom_basis: string | null
  rom_note: string | null
  spec_attributes: Record<string, unknown> | null
  target_building: string | null
  target_area: string | null
  required_by_date: string | null
  is_lle: boolean
  created_at: string
}

export interface Quote {
  id: string
  demand_line_id: string
  vendor: string
  unit_price: number
  lead_time_weeks: number | null
  state: string
}

export interface RomPriceRequest {
  type_query: string
  denominator: string
  size: number
  qty: number
  /** project-level assumptions, as fractions (0.05 = 5%) */
  tariff_pct?: number
  escalation_pct?: number
}

export interface RomBatchLine {
  type_query: string
  denominator: string
  size: number
  qty: number
}

export interface RomPriceBatchRequest {
  lines: RomBatchLine[]
}

export interface RomRollup {
  line_count: number
  priced_count: number
  unpriced_count: number
  total_qty: number
  total_low: number
  total_mid: number
  total_high: number
  confidence_tier: 'high' | 'medium' | 'low' | 'none'
  tier_counts: Record<string, number>
}

export interface RomPriceBatchResponse {
  lines: RomBand[]
  rollup: RomRollup
}

export interface DemandLineCreate {
  project_id: string
  qty: number
  equipment_type_id: string | null
  spec_attributes: Record<string, unknown>
  target_building: string | null
  target_area: string | null
  rom_unit_price: number | null
  rom_confidence: string | null
  rom_comparables_count: number | null
  /** which point of the band was taken, and why — the grid takes the default and sends neither */
  rom_basis?: string
  rom_note?: string | null
  required_by_date?: string | null
  is_lle?: boolean
}

export interface Comparable {
  supplier: string | null
  oem: string | null
  status: string | null
  spec: string | null
  size: number | null
  per_denominator: number
  base_unit: number | null
  services_unit: number | null
  tax_pct: number | null
  source_ref: string | null
}

/** Comparables sharing a supply route — what actually drives the spread. */
export interface ComparableGroup {
  route: string
  supplier: string | null
  oem: string | null
  count: number
  per_denom_low: number
  per_denom_mid: number
  per_denom_high: number
  unit_low: number
  unit_mid: number
  unit_high: number
  layers: Record<string, number>
  comparables: Comparable[]
}

export interface RomBand {
  type_query: string
  denominator: string
  size: number
  qty: number
  comparables_count: number
  confidence_tier: 'high' | 'medium' | 'low' | 'none'
  unit_low: number | null
  unit_mid: number | null
  unit_high: number | null
  extended_mid: number | null
  layers: Record<string, number>
  note: string | null
  groups: ComparableGroup[]
}

/** What a freeze at a given scope would cover, resolved server-side. */
export interface FreezeScopePreview {
  scope: string
  scope_ref: string | null
  line_count: number
  total_qty: number
  rom_extended: number | null
  demand_line_ids: string[]
}

/** A ROM pass over demand that already exists. */
export interface PricedDemandRead {
  priced: DemandLineRow[]
  rollup: RomRollup
  skipped_no_physics: number
}

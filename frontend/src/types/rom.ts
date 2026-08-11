export interface Project {
  id: string
  name: string
  legend_frozen: boolean
}

export interface ProjectLocation {
  id: string
  code: string
  kind: string
  label: string | null
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
  spec_attributes: Record<string, unknown> | null
  target_building: string | null
  target_area: string | null
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
}

export interface RomBatchLine {
  type_query: string
  denominator: string
  size: number
  qty: number
}

export interface RomPriceBatchRequest {
  lines: RomBatchLine[]
  tariff_pct?: number
  escalation_pct?: number
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

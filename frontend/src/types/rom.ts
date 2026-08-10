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

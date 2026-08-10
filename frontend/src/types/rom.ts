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

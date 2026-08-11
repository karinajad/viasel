export interface Agreement {
  id: string
  project_id: string
  code: string
  vendor_id: string | null
  vendor_name: string
  agreement_type: string
  buyer_entity: string | null
  state: string
  issued_date: string | null
  execution_date: string | null
  created_at: string
  line_count: number
  total_qty: number
  /** derived — the sum of the scope lines, never stored */
  contract_value: number
  package_ids: string[]
  package_codes: string[]
}

export interface CoverSheet {
  po_number: string
  date_of_issue: string | null
  site_code: string | null
  project_name: string
  project_address: string | null
  buyer_entity: string | null
  vendor_name: string
  vendor_code: string | null
  vendor_contacts: string[]
}

export interface EquipmentRow {
  design_term: string | null
  equipment_spec: string | null
  vendor_description: string | null
  building: string | null
  area: string | null
  qty: number
  unit_price: number
  extended_price: number
  lead_time_weeks: number | null
  oem: string | null
}

export interface LegendEntry {
  kind: string
  code: string
  description: string | null
}

export interface ExhibitSet {
  agreement: Agreement
  cover_sheet: CoverSheet
  equipment_list: EquipmentRow[]
  legend: LegendEntry[]
  not_yet_derivable: string[]
}

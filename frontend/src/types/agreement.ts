export interface Agreement {
  id: string
  project_id: string
  code: string
  vendor_id: string | null
  vendor_name: string
  agreement_type: string
  buyer_entity: string | null
  state: string
  released_date: string | null
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

export type ExhibitKind =
  | 'delivery_schedule' | 'spare_parts' | 'bill_of_materials'
  | 'shipping_capacity' | 'required_documents'

export const EXHIBIT_KINDS: ExhibitKind[] = [
  'delivery_schedule', 'spare_parts', 'bill_of_materials',
  'shipping_capacity', 'required_documents',
]

/** Schedule D's own standard trigger list, verbatim. */
export const GATES = [
  'Prior to Manufacturing Release', 'Prior to Shipment', 'With Shipment', 'Upon Delivery',
  'Prior to Commissioning', 'Upon Commissioning', 'Prior to Final Payment', 'As Requested', 'N/A',
]

export interface ExhibitItem {
  id: string
  exhibit: string
  scope_line_id: string | null
  equipment_type_id: string | null
  building: string | null
  area: string | null
  description: string
  qty: number | null
  unit_price: number | null
  /** ROJ date · need-by date · period start, depending on the tab */
  due_date: string | null
  vendor_delivery_date: string | null
  designation: string | null
  gate: string | null
  is_included: boolean | null
  is_required: boolean | null
  lead_time_weeks: number | null
  note: string | null
}

/** A committed line — the units allocated to this vendor at sourcing. */
export interface CommittedLine {
  scope_line_id: string
  label: string
  equipment_type_id: string | null
  design_term: string | null
  building: string | null
  area: string | null
  qty: number
  unit_price: number
}

export interface TypeOption {
  equipment_type_id: string | null
  label: string
  unit_count: number
}

export interface LineCoverage {
  scope_line_id: string
  label: string
  committed_qty: number
  scheduled_qty: number
  remaining_qty: number
}

export interface ExhibitSet {
  agreement: Agreement
  cover_sheet: CoverSheet
  equipment_list: EquipmentRow[]
  legend: LegendEntry[]
  items: Record<string, ExhibitItem[]>
  delivery_coverage: LineCoverage[]
  committed_lines: CommittedLine[]
  equipment_types: TypeOption[]
  roj_dates: string[]
}

export interface ExecutedAgreement {
  id: string
  source_system: string
  external_document_ref: string | null
  execution_date: string | null
  stated_po_number: string | null
  stated_buyer_entity: string | null
  stated_vendor_name: string | null
  stated_total_qty: number | null
  stated_contract_value: number | null
  reconciliation_status: string
  retrieved_at: string
  retrieved_by: string | null
}

export interface FieldDivergence {
  id: string
  field_name: string
  generated_value: string | null
  executed_value: string | null
  resolution_note: string | null
}

export interface Reconciliation {
  executed: ExecutedAgreement
  divergences: FieldDivergence[]
}

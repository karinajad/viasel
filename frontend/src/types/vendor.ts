export const VENDOR_ROLES = ['oem', 'distributor', 'integrator', 'supplier']
export const VENDOR_STATUSES = ['prospect', 'approved', 'preferred', 'hold', 'disqualified']

export interface Vendor {
  id: string
  name: string
  code: string | null
  role: string
  oem_names: string[] | null
  factory_country: string | null
  factory_location: string | null
  integration_location: string | null
  sub_supplier: string | null
  status: string
  status_note: string | null
  notes: string | null
  created_at: string
}

export interface VendorContact {
  id: string
  name: string
  title: string | null
  email: string | null
  phone: string | null
}

export interface VendorDetail extends Vendor {
  contacts: VendorContact[]
  bid_count: number
  award_count: number
}

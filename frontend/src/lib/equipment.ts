import type { EquipmentType } from '../types/rom'

/** Size lives inside the sub-type name ("3250kVA" → 3250) — it is read, never typed. */
export const parseSize = (s: string): number | null => {
  const m = s.match(/(\d+(?:\.\d+)?)/)
  return m ? Number(m[1]) : null
}

export const unitTypeCodes = (types: EquipmentType[]): string[] =>
  [...new Set(types.map((t) => t.unit_type_code))].sort()

export const subTypesFor = (types: EquipmentType[], code: string): string[] =>
  types.filter((t) => t.unit_type_code === code && t.sub_type).map((t) => t.sub_type as string)

export const typeRowFor = (types: EquipmentType[], code: string, sub: string): EquipmentType | undefined =>
  types.find((t) => t.unit_type_code === code && (sub ? t.sub_type === sub : true)) ??
  types.find((t) => t.unit_type_code === code)

export interface Spec {
  row: EquipmentType | undefined
  subType: string
  size: number
  denominator: string
}

/**
 * What a requirement resolves to. An equipment type is physics only: pick the type and
 * its size, and the denominator + size fall out of the record — nothing is hand-entered.
 */
export function resolveSpec(types: EquipmentType[], code: string, sub: string): Spec {
  const subs = subTypesFor(types, code)
  const subType = sub && subs.includes(sub) ? sub : subs[0] ?? ''
  const row = typeRowFor(types, code, subType)
  return { row, subType, size: parseSize(subType) ?? 1, denominator: row?.natural_denominator ?? '$/unit' }
}

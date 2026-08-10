import type { DemandLineRow } from '../types/rom'

export const money = (n: number | null | undefined): string =>
  n == null ? '—' : '$' + Math.round(n).toLocaleString()

export const TIER: Record<string, string> = { high: '#2f6f4f', medium: '#b7791f', low: '#b23a3a', none: '#6b7280' }
export const STATE: Record<string, string> = { drafted: '#6b7280', frozen: '#2f6f4f', thawed: '#b23a3a', matching: '#b7791f', matched: '#2f6f4f', satisfied: '#2f6f4f', cancelled: '#9aa0a6' }

/** What a thing is, in one phrase — physics only: type, size, natural unit. */
export const physics = (type: string, size: number | string, denominator: string): string =>
  `${type} ${size}${denominator.replace('$/', ' ')}`.trim()

/** A demand line in one phrase, the way it was captured. */
export const describe = (d: DemandLineRow): string => {
  const a = d.spec_attributes ?? {}
  return physics(String(a.type_query ?? ''), String(a.size ?? ''), String(a.denominator ?? ''))
}

/** A delta that reads as a delta — sign always shown, so parity is unmistakable. */
export const signed = (n: number | null | undefined): string =>
  n == null ? '—' : n === 0 ? 'at par' : `${n > 0 ? '+' : '−'}${money(Math.abs(n))}`

export const signedPct = (p: number | null | undefined): string =>
  p == null || p === 0 ? '' : ` (${p > 0 ? '+' : '−'}${(Math.abs(p) * 100).toFixed(1)}%)`

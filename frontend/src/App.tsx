import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiPost } from './services/api'
import type { RomBand, RomPriceRequest } from './types/rom'

const DENOMS = ['$/kVA', '$/ton', '$/kW', '$/MW', '$/MVA', '$/A', '$/ft', '$/unit']

const PRESETS = [
  { label: '5000 kVA transformer ×12', type: 'Transformer', denominator: '$/kVA', size: 5000, qty: 12 },
  { label: '350 ton chiller ×8', type: 'Chiller', denominator: '$/ton', size: 350, qty: 8 },
  { label: '2000 kW UPS ×4', type: 'UPS', denominator: '$/kW', size: 2000, qty: 4 },
]

const money = (n: number | null): string =>
  n == null ? '—' : '$' + Math.round(n).toLocaleString()

const TIER_COLOR: Record<string, string> = {
  high: '#2f6f4f',
  medium: '#b7791f',
  low: '#b23a3a',
  none: '#6b7280',
}

function App() {
  const [type, setType] = useState('Transformer')
  const [denominator, setDenominator] = useState('$/kVA')
  const [size, setSize] = useState(5000)
  const [qty, setQty] = useState(12)

  const m = useMutation({
    mutationFn: (req: RomPriceRequest) => apiPost<RomBand>('/rom/price', req),
  })
  const band = m.data

  const price = () =>
    m.mutate({ type_query: type, denominator, size: Number(size), qty: Number(qty) })

  const wrap: React.CSSProperties = { fontFamily: 'system-ui, sans-serif', color: '#1a1a1a', maxWidth: 860, margin: '0 auto', padding: '2.5rem 1.5rem' }
  const card: React.CSSProperties = { border: '1px solid #c9ccd1', borderRadius: 12, padding: 18 }
  const label: React.CSSProperties = { fontSize: 12, color: '#6b7280', margin: '10px 0 4px' }
  const field: React.CSSProperties = { width: '100%', padding: '9px 11px', border: '1px solid #c9ccd1', borderRadius: 7, fontSize: 14 }

  return (
    <main style={wrap}>
      <h1 style={{ marginBottom: 2 }}>Viasel — ROM Calculator</h1>
      <p style={{ color: '#6b7280', marginTop: 0 }}>
        Price a requirement from your own executed history, normalized to its natural unit.
      </p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '14px 0' }}>
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => { setType(p.type); setDenominator(p.denominator); setSize(p.size); setQty(p.qty) }}
            style={{ border: '1px solid #c9ccd1', background: '#fff', borderRadius: 999, padding: '5px 12px', fontSize: 12.5, cursor: 'pointer' }}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div style={card}>
          <h3 style={{ marginTop: 0, fontSize: 13, textTransform: 'uppercase', letterSpacing: '.06em', color: '#6b7280' }}>Requirement</h3>
          <div style={label}>Equipment type</div>
          <input style={field} value={type} onChange={(e) => setType(e.target.value)} placeholder="e.g. Transformer" />
          <div style={label}>Natural denominator</div>
          <select style={field} value={denominator} onChange={(e) => setDenominator(e.target.value)}>
            {DENOMS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <div style={label}>Size</div>
              <input style={field} type="number" value={size} onChange={(e) => setSize(Number(e.target.value))} />
            </div>
            <div>
              <div style={label}>Quantity</div>
              <input style={field} type="number" value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            </div>
          </div>
          <button
            onClick={price}
            disabled={m.isPending}
            style={{ marginTop: 16, width: '100%', padding: '10px', background: '#2f6f4f', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}
          >
            {m.isPending ? 'Pricing…' : 'Price it'}
          </button>
        </div>

        <div style={card}>
          <h3 style={{ marginTop: 0, fontSize: 13, textTransform: 'uppercase', letterSpacing: '.06em', color: '#6b7280' }}>Price band</h3>
          {m.isError && <p style={{ color: '#b23a3a' }}>Couldn’t reach the API. Is the backend running on :8000?</p>}
          {!band && !m.isError && <p style={{ color: '#6b7280' }}>Enter a requirement and hit “Price it”.</p>}
          {band && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontVariantNumeric: 'tabular-nums' }}>
                <span>{money(band.unit_low)}</span>
                <strong style={{ fontSize: 22 }}>{money(band.unit_mid)}</strong>
                <span>{money(band.unit_high)}</span>
              </div>
              <div style={{ height: 10, borderRadius: 6, background: 'linear-gradient(90deg,#e7efe9,#bcd8c6,#e7efe9)', border: '1px solid #c9ccd1', margin: '6px 0' }} />
              <div style={{ fontSize: 12, color: '#6b7280' }}>
                per unit ({band.denominator}) · extended <strong>{money(band.extended_mid)}</strong> (×{band.qty})
              </div>
              <div style={{ marginTop: 12, fontSize: 13 }}>
                Confidence:{' '}
                <strong style={{ color: TIER_COLOR[band.confidence_tier] }}>{band.confidence_tier}</strong>
                {' '}· {band.comparables_count} comparables
              </div>
              {band.note && <p style={{ fontSize: 12.5, color: '#b7791f', marginTop: 10 }}>{band.note}</p>}
              <div style={{ marginTop: 14, fontSize: 12, color: '#444' }}>
                <div style={{ color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 4 }}>Layers</div>
                base {money(band.layers.base)} · services {money(band.layers.services)} · freight {money(band.layers.freight)} · tax {(band.layers.tax_pct * 100).toFixed(2)}%
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  )
}

export default App

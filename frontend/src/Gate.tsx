import { useState } from 'react'

// Light gate: keeps casual visitors out of the deployed demo. Not real security
// (the password ships in the bundle) — use Vercel Password Protection or backend
// auth when a real lock is needed.
const PASSWORD = 'viasel'

export function Gate({ children }: { children: React.ReactNode }) {
  const [ok, setOk] = useState(() => sessionStorage.getItem('viasel_auth') === '1')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState(false)

  if (ok) return <>{children}</>

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (pw === PASSWORD) {
      sessionStorage.setItem('viasel_auth', '1')
      setOk(true)
    } else {
      setErr(true)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'system-ui, sans-serif', background: '#f4f5f7' }}>
      <form onSubmit={submit} style={{ background: '#fff', border: '1px solid #c9ccd1', borderRadius: 12, padding: 28, width: 300, textAlign: 'center' }}>
        <h1 style={{ margin: '0 0 4px' }}>Viasel</h1>
        <p style={{ color: '#6b7280', marginTop: 0, fontSize: 13 }}>Enter password to continue</p>
        <input
          type="password"
          value={pw}
          autoFocus
          onChange={(e) => { setPw(e.target.value); setErr(false) }}
          placeholder="password"
          style={{ width: '100%', padding: '10px 12px', border: `1px solid ${err ? '#b23a3a' : '#c9ccd1'}`, borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
        />
        <button type="submit" style={{ marginTop: 12, width: '100%', padding: '10px', background: '#2f6f4f', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}>
          Enter
        </button>
        {err && <p style={{ color: '#b23a3a', fontSize: 12.5, marginBottom: 0 }}>Incorrect password</p>}
      </form>
    </div>
  )
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const API_TOKEN = import.meta.env.VITE_API_TOKEN ?? 'viasel-dev'

interface ValidationItem { loc?: (string | number)[]; msg?: string }

/**
 * Fail with what the API actually said. A gate violation carries its reason in `detail`
 * (409) and a bad field carries which field (422) — showing a bare status code throws
 * away the only useful part.
 */
async function fail(res: Response, method: string, path: string): Promise<never> {
  let detail = ''
  try {
    const body: unknown = await res.json()
    const d = (body as { detail?: unknown })?.detail
    if (typeof d === 'string') detail = d
    else if (Array.isArray(d)) {
      detail = (d as ValidationItem[])
        .map((i) => `${(i.loc ?? []).slice(1).join('.') || 'request'}: ${i.msg ?? 'invalid'}`)
        .join(' · ')
    }
  } catch {
    // no JSON body — fall back to the status line
  }
  throw new Error(detail || `${method} ${path} failed: ${res.status}`)
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { headers: { 'X-API-Key': API_TOKEN } })
  if (!res.ok) await fail(res, 'GET', path)
  return res.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_TOKEN },
    body: JSON.stringify(body),
  })
  if (!res.ok) await fail(res, 'POST', path)
  return res.json() as Promise<T>
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_TOKEN },
    body: JSON.stringify(body),
  })
  if (!res.ok) await fail(res, 'PATCH', path)
  return res.json() as Promise<T>
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, { method: 'DELETE', headers: { 'X-API-Key': API_TOKEN } })
  if (!res.ok) await fail(res, 'DELETE', path)
}

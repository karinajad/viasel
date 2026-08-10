const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const API_TOKEN = import.meta.env.VITE_API_TOKEN ?? 'viasel-dev'

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { headers: { 'X-API-Key': API_TOKEN } })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_TOKEN },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_TOKEN },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, { method: 'DELETE', headers: { 'X-API-Key': API_TOKEN } })
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
}

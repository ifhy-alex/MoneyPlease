export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `Error ${status}`)
    this.status = status
    this.detail = detail
  }
}

type Params = Record<string, string | number | boolean | undefined | null>

function url(path: string, params?: Params): string {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== null && v !== '' && v !== false) qs.set(k, String(v))
  }
  const s = qs.toString()
  return `/api${path}${s ? `?${s}` : ''}`
}

async function request<T>(method: string, path: string, body?: unknown, params?: Params): Promise<T> {
  const init: RequestInit = { method, headers: {} }
  if (body instanceof FormData) init.body = body
  else if (body !== undefined) {
    init.body = JSON.stringify(body)
    init.headers = { 'Content-Type': 'application/json' }
  }
  const resp = await fetch(url(path, params), init)
  if (!resp.ok) {
    let detail: unknown = resp.statusText
    try {
      detail = (await resp.json()).detail
    } catch {
      /* sin cuerpo JSON */
    }
    throw new ApiError(resp.status, detail)
  }
  return resp.status === 204 ? (undefined as T) : resp.json()
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>('GET', path, undefined, params),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError && typeof err.detail === 'string') return err.detail
  if (err instanceof Error) return err.message
  return 'Algo salió mal'
}

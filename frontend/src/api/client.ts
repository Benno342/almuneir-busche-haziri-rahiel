// Thin fetch wrapper for the FastAPI backend.
// Domain errors arrive as {"error": "<ExceptionClass>", "detail": "<message>"}.

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number
  readonly error: string

  constructor(status: number, error: string, detail: string) {
    super(detail)
    this.status = status
    this.error = error
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.error ?? 'HttpError', body.detail ?? response.statusText)
  }
  return (await response.json()) as T
}

/**
 * Base HTTP client.
 */

import { toast } from 'sonner'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type RequestOptions = {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  silent?: boolean  // Don't show toast on error
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, silent = false } = options

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({ message: 'Something went wrong' }))
      const message = data.message || data.detail || 'Something went wrong'
      if (!silent) toast.error(message)
      throw new ApiError(message, res.status)
    }

    return res.json()
  } catch (err) {
    if (err instanceof ApiError) throw err
    const message = 'Could not connect to server'
    if (!silent) toast.error(message)
    throw new ApiError(message, 0)
  }
}

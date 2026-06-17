/**
 * API client — HTTP calls to the backend REST endpoints.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export type EventPayload = {
  event_id: string
  thread_id: string
  user_id: string
  text: string
  channel: 'web' | 'mobile' | 'whatsapp'
  input_type: 'text' | 'voice'
  selected_option_id?: string
  metadata?: Record<string, unknown>
}

export type EventResponse = {
  event_id: string
  status: string
}

export async function sendEvent(payload: EventPayload): Promise<EventResponse> {
  const res = await fetch(`${BASE_URL}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }

  return res.json()
}

export async function healthCheck(): Promise<{ status: string; service: string }> {
  const res = await fetch(`${BASE_URL}/health`)
  return res.json()
}

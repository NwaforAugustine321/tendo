/**
 * Events service — send unified events to the backend.
 */

import { request } from './http'

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
  return request<EventResponse>('/events', {
    method: 'POST',
    body: payload,
  })
}

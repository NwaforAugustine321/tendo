/**
 * Conversations service — sessions and messages.
 */

import { request } from './http'

export type ChatSession = {
  id: string
  title: string
  status: string
  record_id?: string | null
  created_at: string
  updated_at: string
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

export async function listSessions(businessId: string, recordId?: string): Promise<ChatSession[]> {
  const params = recordId ? `&record_id=${recordId}` : ''
  return await request<ChatSession[]>(`/conversations/sessions?business_id=${businessId}${params}`, { silent: true })
}

export async function createSession(businessId: string, title: string = 'New Session', recordId?: string): Promise<ChatSession> {
  const body: Record<string, string> = { business_id: businessId, title }
  if (recordId) body.record_id = recordId
  return await request<ChatSession>('/conversations/sessions', {
    method: 'POST',
    body,
  })
}

export async function getSessionMessages(sessionId: string, businessId: string, limit: number = 20, offset: number = 0): Promise<ChatMessage[]> {
  return await request<ChatMessage[]>(
    `/conversations/sessions/${sessionId}/messages?business_id=${businessId}&limit=${limit}&offset=${offset}`,
    { silent: true }
  )
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<ChatSession> {
  return await request<ChatSession>(`/conversations/sessions/${sessionId}`, {
    method: 'PUT',
    body: { title },
  })
}

export async function deleteSession(sessionId: string, businessId: string): Promise<void> {
  await request(`/conversations/sessions/${sessionId}?business_id=${businessId}`, {
    method: 'DELETE',
  })
}

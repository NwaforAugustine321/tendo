/**
 * Conversations service — sessions and messages.
 */

import { request } from './http'

export type ChatSession = {
  id: string
  title: string
  status: string
  created_at: string
  updated_at: string
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

export async function listSessions(businessId: string): Promise<ChatSession[]> {
  return await request<ChatSession[]>(`/conversations/sessions?business_id=${businessId}`, { silent: true })
}

export async function createSession(businessId: string, title: string = 'New Session'): Promise<ChatSession> {
  return await request<ChatSession>('/conversations/sessions', {
    method: 'POST',
    body: { business_id: businessId, title },
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

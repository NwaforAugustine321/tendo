/**
 * Auth service — login, register, logout, session.
 */

import { request } from './http'

export type AuthUser = {
  user_id: string
  email: string
  name: string
}

export async function login(email: string, password: string): Promise<AuthUser> {
  return request<AuthUser>('/auth/login', {
    method: 'POST',
    body: { email, password },
  })
}

export async function register(email: string, password: string, name: string): Promise<AuthUser> {
  return request<AuthUser>('/auth/register', {
    method: 'POST',
    body: { email, password, name },
  })
}

export async function logout(): Promise<void> {
  await request('/auth/logout', { method: 'POST' })
}

export async function getMe(): Promise<AuthUser | null> {
  try {
    return await request<AuthUser>('/auth/me')
  } catch {
    return null
  }
}

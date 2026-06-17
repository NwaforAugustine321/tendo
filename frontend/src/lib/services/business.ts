import { request } from './http'

export type BusinessProfile = {
  id: string
  business_id: string
  name?: string
  email?: string
}

export async function getProfiles(): Promise<BusinessProfile[]> {
  const res = await request<{ profiles: BusinessProfile[] }>('/business/profiles', { silent: true })
  return res.profiles
}

export async function startOnboarding(): Promise<string> {
  const res = await request<{ message: string }>('/business/onboarding/start', { method: 'POST' })
  return res.message
}

import { request } from './http'

export type BusinessProfile = {
  id: string
  user_id: string
  name: string
  category: string
  description: string
  phone: string
  location: string
  logo_url: string
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export type CreateEmptyBusinessResponse = {
  business_id: string
  session_id: string
}

export type ResumeSessionResponse = {
  session_id: string
  business_id: string
}

export async function getProfiles(): Promise<BusinessProfile[]> {
  const res = await request<{ profiles: BusinessProfile[] }>('/business/profiles', { silent: true })
  return res.profiles
}

export async function createEmptyBusiness(): Promise<CreateEmptyBusinessResponse> {
  return await request<CreateEmptyBusinessResponse>('/business/create-empty', { method: 'POST' })
}

export async function resumeSession(businessId: string): Promise<ResumeSessionResponse> {
  return await request<ResumeSessionResponse>('/business/resume-session', {
    method: 'POST',
    body: { business_id: businessId },
  })
}

export async function getProfile(businessId: string): Promise<BusinessProfile | null> {
  try {
    const res = await request<{ profile: BusinessProfile }>(`/business/profile/${businessId}`, { silent: true })
    return res.profile
  } catch {
    return null
  }
}

export async function deleteBusinessProfile(businessId: string): Promise<void> {
  await request(`/business/profile/${businessId}`, { method: 'DELETE' })
}

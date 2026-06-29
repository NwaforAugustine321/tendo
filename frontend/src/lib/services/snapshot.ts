/**
 * Snapshot API service for the dashboard.
 */

import { request } from './http'

export type SnapshotStory = {
  title: string
  narrative: string
  area: string
  sentiment: 'positive' | 'neutral' | 'attention_needed'
}

export type SnapshotRecommendation = {
  action: string
  reason: string
  priority: 'high' | 'medium' | 'low'
}

export type BusinessSnapshot = {
  id: string
  business_id: string
  stories: SnapshotStory[]
  recommendations: SnapshotRecommendation[]
  created_at: string
}

/**
 * Fetch the latest business snapshot.
 * Returns null if no snapshot exists yet.
 * @param businessId - The business to fetch the snapshot for
 */
export async function getSnapshot(
  businessId: string
): Promise<BusinessSnapshot | null> {
  try {
    return await request<BusinessSnapshot>(
      `/business/${businessId}/snapshot`,
      { silent: true }
    )
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'status' in err && (err as { status: number }).status === 404) {
      return null
    }
    throw err
  }
}

/**
 * Force regenerate the business snapshot.
 * @param businessId - The business to refresh the snapshot for
 */
export async function refreshSnapshot(
  businessId: string
): Promise<BusinessSnapshot> {
  return request<BusinessSnapshot>(
    `/business/${businessId}/snapshot/refresh`,
    { method: 'POST' }
  )
}

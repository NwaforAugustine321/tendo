/**
 * Insights API service for the dashboard.
 */

import { request } from './http'
import type { BusinessInsight, DashboardStats, TimeRange } from '../workspace/dashboard-types'

/**
 * Fetch business insights from the API.
 * @param businessId - The business to fetch insights for
 * @param limit - Optional max number of insights to return
 */
export async function getInsights(
  businessId: string,
  limit?: number
): Promise<BusinessInsight[]> {
  const params = limit ? `?limit=${limit}` : ''
  return request<BusinessInsight[]>(
    `/business/${businessId}/insights${params}`,
    { silent: true }
  )
}

/**
 * Fetch dashboard stats for a given time range.
 * @param businessId - The business to fetch stats for
 * @param range - Time range filter
 */
export async function getInsightStats(
  businessId: string,
  range: TimeRange
): Promise<DashboardStats> {
  return request<DashboardStats>(
    `/business/${businessId}/stats?range=${range}`,
    { silent: true }
  )
}

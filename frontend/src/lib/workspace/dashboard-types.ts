/**
 * Data types for the Dashboard Redesign feature.
 */

import type { LucideIcon } from 'lucide-react'

/** Insight area categories matching business_insights table */
export type InsightArea =
  | 'sales'
  | 'finance'
  | 'operations'
  | 'customers'
  | 'inventory'
  | 'general'
  | 'hr'
  | 'marketing'

/** Derived status for insight display */
export type InsightStatus = 'growing' | 'stable' | 'needs-attention'

/** Time range for filtering dashboard data */
export type TimeRange = 'today' | 'yesterday' | '7d' | '30d'

/** Raw insight data from API (matches business_insights table) */
export interface BusinessInsight {
  id: string
  business_id: string
  insight: string
  area: InsightArea
  importance: number
  source_agent: string
  payload: Record<string, unknown>
  created_at: string
}

/** Mapped insight card for dashboard display */
export interface DashboardInsightCard {
  id: string
  area: InsightArea
  icon: LucideIcon
  categoryName: string
  status: InsightStatus
  summary: string
  metadata: string
  updatedAt: string
  rawInsight: BusinessInsight
}

/** Single stat value with change indicator */
export interface StatValue {
  current: number
  changePercent: number
}

/** Stats bar data for the dashboard bottom bar */
export interface DashboardStats {
  revenue: StatValue
  transactions: StatValue
  topCategory: { name: string; percentage: number }
  newCustomers: StatValue
}

/** Dashboard UI state (added to workspace store) */
export interface DashboardUIState {
  sidebarVisible: boolean
  chatPanelVisible: boolean
  characterFlipped: boolean
  timeRange: TimeRange
  quickActionsOpen: boolean
}

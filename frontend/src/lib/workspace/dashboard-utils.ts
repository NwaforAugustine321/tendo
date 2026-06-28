/**
 * Pure utility functions for the Dashboard Redesign feature.
 */

import type { BusinessInsight, InsightArea, InsightStatus } from './dashboard-types'

/**
 * Derives the display status of a business insight based on its payload and importance.
 *
 * - 'growing' if payload.growth > 0
 * - 'needs-attention' if importance >= 0.8 or payload.alert is truthy
 * - 'stable' otherwise
 */
export function deriveStatus(insight: BusinessInsight): InsightStatus {
  const { payload, importance } = insight
  if (payload.growth && (payload.growth as number) > 0) return 'growing'
  if (importance >= 0.8 || payload.alert) return 'needs-attention'
  return 'stable'
}

/**
 * Returns a time-of-day greeting string based on the given hour (0-23).
 *
 * - "Good morning" for hours 5-11
 * - "Good afternoon" for hours 12-17
 * - "Good evening" for hours 18-23 and 0-4
 */
export function getGreeting(hour: number): string {
  if (hour >= 5 && hour <= 11) return 'Good morning'
  if (hour >= 12 && hour <= 17) return 'Good afternoon'
  return 'Good evening'
}

/**
 * Maps an InsightStatus to Tailwind CSS classes for the status badge.
 */
export function getStatusBadgeColor(status: InsightStatus): string {
  switch (status) {
    case 'growing':
      return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30'
    case 'stable':
      return 'text-blue-400 bg-blue-400/10 border-blue-400/30'
    case 'needs-attention':
      return 'text-orange-400 bg-orange-400/10 border-orange-400/30'
  }
}

/** Angle mappings for each insight area positioned radially around center */
const AREA_ANGLES: Record<string, number> = {
  finance: -90,    // top
  customers: 180,  // left
  operations: -30, // top-right
  sales: 90,       // bottom
  general: 0,      // right
  inventory: 210,  // bottom-left
}

/**
 * Returns the x,y pixel coordinates for an InsightArea positioned radially
 * around the center of a container.
 *
 * Radius is ~40% of the smaller dimension. Coordinates are clamped within bounds.
 */
export function getRadialPosition(
  area: InsightArea,
  containerWidth: number,
  containerHeight: number
): { x: number; y: number } {
  const centerX = containerWidth / 2
  const centerY = containerHeight / 2
  const radius = Math.min(containerWidth, containerHeight) * 0.4

  const angleDeg = AREA_ANGLES[area] ?? 0
  const angleRad = (angleDeg * Math.PI) / 180

  const rawX = centerX + radius * Math.cos(angleRad)
  const rawY = centerY + radius * Math.sin(angleRad)

  // Clamp within container bounds
  const x = Math.max(0, Math.min(containerWidth, rawX))
  const y = Math.max(0, Math.min(containerHeight, rawY))

  return { x, y }
}

/**
 * Returns a Tailwind text color class for a stat change indicator.
 *
 * - Positive change → green
 * - Negative change → red
 * - Zero change → neutral
 */
export function getChangeIndicatorColor(changePercent: number): string {
  if (changePercent > 0) return 'text-emerald-400'
  if (changePercent < 0) return 'text-red-400'
  return 'text-zinc-400'
}

/**
 * Aggregations for the Snap overview.
 *
 * Pure functions over the Snaps the Inbox already loaded, so the overview
 * costs no extra requests. Shares are fractions in the 0..1 range.
 */

import type { Snap, SnapPriority, SnapType } from "../services/snaps";

export const PRIORITY_ORDER: SnapPriority[] = [
  "critical",
  "high",
  "medium",
  "low",
];

export const TYPE_ORDER: SnapType[] = [
  "warning",
  "attention",
  "opportunity",
  "recommendation",
];

const URGENT: SnapPriority[] = ["critical", "high"];

export type Slice<T extends string> = {
  key: T;
  count: number;
  share: number;
};

export type DomainSlice = {
  key: string;
  count: number;
  share: number;
  avgConfidence: number;
  urgentCount: number;
};

export type SnapOverviewData = {
  total: number;
  activeCount: number;
  savedCount: number;
  avgConfidence: number;
  urgentShare: number;
  urgentCount: number;
  priorities: Slice<SnapPriority>[];
  types: Slice<SnapType>[];
  domains: DomainSlice[];
};

function share(count: number, total: number): number {
  return total > 0 ? count / total : 0;
}

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function buildSnapOverview(
  active: Snap[],
  saved: Snap[],
): SnapOverviewData {
  const all = [...active, ...saved];
  const total = all.length;

  const urgentCount = all.filter((snap) =>
    URGENT.includes(snap.priority),
  ).length;

  const priorities = PRIORITY_ORDER.map((key) => {
    const count = all.filter((snap) => snap.priority === key).length;
    return { key, count, share: share(count, total) };
  });

  const types = TYPE_ORDER.map((key) => {
    const count = all.filter((snap) => snap.type === key).length;
    return { key, count, share: share(count, total) };
  });

  const domains: DomainSlice[] = [...new Set(all.map((snap) => snap.domain))]
    .map((key) => {
      const group = all.filter((snap) => snap.domain === key);
      return {
        key,
        count: group.length,
        share: share(group.length, total),
        avgConfidence: mean(group.map((snap) => snap.confidence)),
        urgentCount: group.filter((snap) => URGENT.includes(snap.priority))
          .length,
      };
    })
    .sort((a, b) => b.count - a.count || b.avgConfidence - a.avgConfidence);

  return {
    total,
    activeCount: active.length,
    savedCount: saved.length,
    avgConfidence: mean(all.map((snap) => snap.confidence)),
    urgentShare: share(urgentCount, total),
    urgentCount,
    priorities,
    types,
    domains,
  };
}

export function toPercent(fraction: number): number {
  return Math.round(fraction * 100);
}

/**
 * Snap feed API service.
 *
 * The attention and recommendation tabs are served live from Redis. The
 * priority tab holds Snaps the user saved and is served from the database.
 */

import { request } from "./http";

export type SnapTab = "attention" | "recommendation" | "priority";

export type SnapType =
  | "recommendation"
  | "attention"
  | "warning"
  | "opportunity";

export type SnapPriority = "low" | "medium" | "high" | "critical";

export type SnapStatus = "active" | "pending" | "completed";

export type Snap = {
  snap_id: string;
  business_id: string;
  type: SnapType;
  priority: SnapPriority;
  confidence: number;
  title: string;
  message: string;
  why_it_matters: string;
  action: string;
  domain: string;
  status: SnapStatus;
  created_at: string | null;
};

type SnapListResponse = {
  snaps: Snap[];
  tab: SnapTab;
  count: number;
};

type SnapResponse = {
  snap: Snap;
};

/**
 * Fetch Snaps for a tab.
 * @param businessId - The business to fetch Snaps for
 * @param tab - Which tab to populate
 * @param limit - Maximum Snaps to return
 */
export async function listSnaps(
  businessId: string,
  tab: SnapTab,
  limit?: number,
): Promise<Snap[]> {
  const params = new URLSearchParams({ tab });
  if (limit) params.set("limit", String(limit));

  const { snaps } = await request<SnapListResponse>(
    `/snaps/${businessId}?${params}`,
    { silent: true },
  );
  return snaps;
}

/**
 * Save a Snap, moving it to the priority tab.
 */
export async function saveSnap(
  businessId: string,
  snapId: string,
): Promise<Snap> {
  const { snap } = await request<SnapResponse>(
    `/snaps/${businessId}/${snapId}/save`,
    { method: "POST" },
  );
  return snap;
}

/**
 * Mark a Snap completed, removing it from every tab.
 */
export async function completeSnap(
  businessId: string,
  snapId: string,
): Promise<Snap> {
  const { snap } = await request<SnapResponse>(
    `/snaps/${businessId}/${snapId}/complete`,
    { method: "POST" },
  );
  return snap;
}

import { useState, useEffect, useRef, useCallback } from "react";
import { useBusinessStore } from "../../store/business";
import { useWorkspaceStore } from "../../store/workspace";
import { GreetingHeader, SnapshotView } from "../../components/containers";
import { getSnapshot } from "../../lib/services/snapshot";
import type { BusinessSnapshot } from "../../lib/services/snapshot";

const POLL_INTERVAL_MS = 30 * 60 * 1000; // 30 minutes

export function Dashboard() {
  const { currentProfile } = useBusinessStore();
  //   const { setDashboardSidebarVisible, setDashboardChatVisible } =
  //     useWorkspaceStore();

  const [snapshot, setSnapshot] = useState<BusinessSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // No longer hide sidebar/chat — this page is now a subpage, not the home

  const fetchSnapshot = useCallback(
    (showLoading = false) => {
      if (!currentProfile?.id) return;
      if (showLoading) setSnapshotLoading(true);
      getSnapshot(currentProfile.id)
        .then((data) => setSnapshot(data))
        .catch(() => setSnapshot(null))
        .finally(() => setSnapshotLoading(false));
    },
    [currentProfile?.id],
  );

  // Fetch snapshot on mount + poll every 30 minutes
  useEffect(() => {
    if (!currentProfile?.id) {
      setSnapshotLoading(false);
      return;
    }

    // Initial fetch
    fetchSnapshot(true);

    // Poll every 30 minutes
    pollRef.current = setInterval(() => fetchSnapshot(false), POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [currentProfile?.id, fetchSnapshot]);

  return (
    <div className="relative flex flex-col h-full overflow-hidden bg-[#0a0a0a]">
      {/* Greeting header */}
      <GreetingHeader
        name={currentProfile?.name || "there"}
        recommendations={snapshot?.recommendations || []}
      />

      {/* Snapshot view — scrollable area */}
      <div className="flex-1 overflow-y-auto relative">
        <SnapshotView snapshot={snapshot} loading={snapshotLoading} />
      </div>
    </div>
  );
}

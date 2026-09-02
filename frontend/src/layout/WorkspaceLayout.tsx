import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { TopBar } from "../components/containers";
import { Sidebar } from "../components/containers/Sidebar";
import { RightRail } from "../components/containers/RightRail";
import { RecordFloatingPanel } from "../components/containers/RecordFloatingPanel";
import { ProcessingNotification } from "../components/atoms/ProcessingNotification";

import { useWorkspaceStore } from "../store/workspace";
import { useAuthStore } from "../store/auth";
import { useBusinessStore } from "../store/business";
import { useVoiceStore } from "../store/voice";
import { useEventReceiver } from "../hooks/useEmitReceiver";

export function WorkspaceLayout() {
  const location = useLocation();

  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  const { toggleDashboardSidebar } = useWorkspaceStore();
  const { user } = useAuthStore();
  const { currentProfile } = useBusinessStore();
  const { startAgent, stopAgent, setStatusText } = useVoiceStore();

  const isDashboard =
    location.pathname === "/me" || location.pathname === "/me/";

  // Connect to voice agent when workspace mounts,
  // disconnect when the workspace unmounts.
  // Guard against calling before auth session is established — the voice
  // endpoint uses cookie auth, so the cookie must be present first.
  useEffect(() => {
    if (!currentProfile?.id || !user) return;

    startAgent({
      businessId: currentProfile.id,
    });

    return () => {
      stopAgent();
    };
  }, [currentProfile?.id, user]);

  // Listen for agent.progress events.
  const { events: agentProgressEvents } = useEventReceiver(["agent.progress"]);

  useEffect(() => {
    if (agentProgressEvents.length === 0) return;

    const latest = agentProgressEvents[agentProgressEvents.length - 1];

    const data = latest.data as any;

    const status = data?.payload?.status || "";
    const message = data?.payload?.message || data?.message || "";

    if (
      status === "completed" ||
      status === "failed" ||
      status === "cancelled"
    ) {
      setStatusText("");
      return;
    }

    if (message) {
      setStatusText(message);
    }
  }, [agentProgressEvents]);

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      {/* Top bar */}
      <TopBar
        onMenuClick={() => {
          if (isDashboard) {
            toggleDashboardSidebar();
          } else {
            setMobileNavOpen(true);
          }
        }}
      />

      <div className="flex min-h-0 min-w-0 flex-1">
        {/* Desktop sidebar */}
        <div className="hidden min-h-0 max-h-full md:flex">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>

        {/* Main content area */}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-[#0a0a0a]">
          <div className="flex h-full min-h-0 w-full min-w-0 flex-col justify-start">
            <Outlet />
          </div>
        </main>

        {/* Right rail */}
        <RightRail />

        {/* Floating record panel */}
        <RecordFloatingPanel />
      </div>

      {/* Mobile navigation overlay */}
      {mobileNavOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/70 md:hidden"
            aria-label="Close menu"
            onClick={() => setMobileNavOpen(false)}
          />

          <div className="fixed inset-y-0 left-0 z-50 flex w-[min(280px,92vw)] flex-col border-r border-zinc-800/90 bg-[#0f0f0f] shadow-2xl md:hidden">
            <Sidebar
              className="w-full"
              collapsed={false}
              onToggle={() => setMobileNavOpen(false)}
            />
          </div>
        </>
      )}

      {/* Processing notifications */}
      <ProcessingNotification />
    </div>
  );
}

import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { TopBar } from "../components/containers";
import { Sidebar } from "../components/containers/Sidebar";
import { RightRail } from "../components/containers/RightRail";
import { WorkspaceContent } from "../components/containers/WorkspaceContent";
import { RecordFloatingPanel } from "../components/containers/RecordFloatingPanel";
import { ProcessingNotification } from "../components/atoms/ProcessingNotification";
import { useWorkspaceStore } from "../store/workspace";
import { useBusinessStore } from "../store/business";
import { useVoiceStore } from "../store/voice";
import { connectSocket } from "../lib/ws";

export function WorkspaceLayout() {
  const location = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  const { toggleDashboardSidebar } = useWorkspaceStore();
  const { currentProfile } = useBusinessStore();
  const { startAgent, stopAgent, setStatusText } = useVoiceStore();

  const isDashboard =
    location.pathname === "/app" || location.pathname === "/app/";

  // Connect to voice agent when workspace mounts, disconnect on unmount
  useEffect(() => {
    if (!currentProfile?.id) return;

    startAgent({ businessId: currentProfile.id });

    return () => {
      stopAgent();
    };
  }, [currentProfile?.id]);

  // Listen for progress events from Socket.IO and forward to voice store.
  useEffect(() => {
    const socket = connectSocket();

    const handler = (raw: any) => {
      const event = typeof raw === "string" ? JSON.parse(raw) : raw;
      const status =
        event?.data?.payload?.status || event?.payload?.status || "";
      const message =
        event?.data?.payload?.message ||
        event?.payload?.message ||
        event?.payload?.payload?.message ||
        event?.message ||
        "";

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
    };

    socket.on("progress", handler);

    return () => {
      socket.off("progress", handler);
    };
  }, []);

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      {/* Top bar — unchanged */}
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
        {/* Gmail-style collapsible left sidebar — desktop */}
        <div className="hidden md:flex min-h-0 max-h-full">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>

        {/* Main content area */}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-[#0a0a0a]">
          <div className="flex min-h-0 w-full min-w-0 flex-col justify-start h-full">
            <WorkspaceContent />
          </div>
        </main>

        <RightRail />

        <RecordFloatingPanel />
      </div>

      {/* Mobile nav overlay */}
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

      {/* Processing notifications — top right corner */}
      <ProcessingNotification />
    </div>
  );
}

import { useState } from "react";

import { Outlet, useLocation } from "react-router-dom";

import { TopBar } from "../components/containers";

import { Sidebar } from "../components/containers/Sidebar";

import { RightRail } from "../components/containers/RightRail";

import { RecordFloatingPanel } from "../components/containers/RecordFloatingPanel";

import { ProcessingNotification } from "../components/atoms/ProcessingNotification";

import { useWorkspaceStore } from "../store/workspace";

export function WorkspaceLayout() {
  const location = useLocation();

  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  const { toggleDashboardSidebar } = useWorkspaceStore();

  const isDashboard =
    location.pathname === "/me" || location.pathname === "/me/";

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
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
        <div className="hidden min-h-0 max-h-full md:flex">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>

        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-[#0a0a0a]">
          <div className="flex h-full min-h-0 w-full min-w-0 flex-col justify-start">
            <Outlet />
          </div>
        </main>

        <RightRail />

        <RecordFloatingPanel />
      </div>

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

      <ProcessingNotification />
    </div>
  );
}

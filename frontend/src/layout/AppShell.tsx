import { Outlet } from 'react-router-dom'

export function AppShell() {
  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <main className="min-h-0 flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}

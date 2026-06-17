import { Link } from 'react-router-dom'

const RECENT_SESSIONS = [
  { id: '1', title: 'Morning Sales Update', lastMessage: 'Sold 5 bags of rice to Musa', time: '2 hours ago' },
  { id: '2', title: 'Inventory Review', lastMessage: 'Rice stock is running low', time: '5 hours ago' },
  { id: '3', title: 'Customer Debt Follow-up', lastMessage: 'Musa owes ₦45,000', time: 'Yesterday' },
]

export function WorkspaceHome() {
  return (
    <div className="px-3 py-5 sm:px-5 sm:py-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-xl font-bold tracking-[-0.02em] text-white">Good morning</h1>
          <p className="mt-1 text-sm text-zinc-500">What would you like to do today?</p>
        </div>

        {/* Quick action — new conversation */}
        <Link
          to="/app/conversation/new"
          className="mb-6 flex items-center gap-3 rounded-xl border border-[#2e2e2e] bg-[#1c1c1c] p-4 transition-colors duration-200 hover:border-[#3ecf8e]/30 hover:bg-[#232323]"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#3ecf8e]/30 bg-[#3ecf8e]/10">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 5v14M5 12h14" stroke="#3ecf8e" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">New Conversation</p>
            <p className="text-xs text-zinc-500">Start recording your business activity</p>
          </div>
        </Link>

        {/* Recent sessions */}
        <div>
          <h2 className="av-kicker mb-3">Recent Sessions</h2>
          <div className="space-y-2">
            {RECENT_SESSIONS.map((session) => (
              <Link
                key={session.id}
                to={`/app/conversation/${session.id}`}
                className="av-dashboard-surface-interactive flex items-center gap-3"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#232323]">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" stroke="currentColor" strokeWidth="1.5" className="text-zinc-500" />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-zinc-200">{session.title}</p>
                  <p className="truncate text-xs text-zinc-500">{session.lastMessage}</p>
                </div>
                <time className="shrink-0 text-[10px] text-zinc-600">{session.time}</time>
              </Link>
            ))}
          </div>
        </div>

        {/* Stat tiles */}
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="av-dashboard-stat-tile">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-600">Today's Sales</p>
            <p className="mt-1 text-lg font-bold tabular-nums tracking-tight text-white">₦125,000</p>
          </div>
          <div className="av-dashboard-stat-tile">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-600">Outstanding</p>
            <p className="mt-1 text-lg font-bold tabular-nums tracking-tight text-white">₦340,000</p>
          </div>
          <div className="av-dashboard-stat-tile">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-600">Low Stock</p>
            <p className="mt-1 text-lg font-bold tabular-nums tracking-tight text-amber-400">3 items</p>
          </div>
          <div className="av-dashboard-stat-tile">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-600">Customers</p>
            <p className="mt-1 text-lg font-bold tabular-nums tracking-tight text-white">24</p>
          </div>
        </div>
      </div>
    </div>
  )
}

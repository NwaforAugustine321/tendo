import { RefreshCw, Trash2, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import type { InboxTab } from './types'
import { TABS } from './types'

type Props = {
  selectedCount: number
  totalCount: number
  activeTab: InboxTab
  unreadCount: number
  loading: boolean
  deleting: boolean
  onSelectAll: () => void
  onDelete: () => void
  onRefresh: () => void
  onTabChange: (tab: InboxTab) => void
}

export function InboxToolbar({
  selectedCount, totalCount, activeTab, unreadCount, loading, deleting,
  onSelectAll, onDelete, onRefresh, onTabChange,
}: Props) {
  return (
    <>
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-zinc-800/60 px-4 py-2">
        <button
          type="button"
          onClick={onSelectAll}
          className={clsx(
            'flex h-4 w-4 items-center justify-center rounded border transition-colors',
            selectedCount > 0 ? 'border-emerald-500 bg-emerald-500' : 'border-zinc-600 hover:border-zinc-500'
          )}
          aria-label="Select all"
        >
          {selectedCount > 0 && selectedCount === totalCount && (
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          )}
          {selectedCount > 0 && selectedCount < totalCount && (
            <span className="h-0.5 w-2.5 bg-white" />
          )}
        </button>
        {selectedCount > 0 && (
          <button type="button" onClick={onDelete} disabled={deleting} className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200 disabled:opacity-50" aria-label="Delete selected">
            {deleting ? <RefreshCw size={16} className="animate-spin" /> : <Trash2 size={16} />}
          </button>
        )}
        <button type="button" onClick={onRefresh} className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200" aria-label="Refresh">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>

        <div className="flex-1">
          <div className="relative w-full max-w-[440px]">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search records..."
              className="h-8 w-full rounded-lg bg-zinc-800/50 pl-8 pr-3 text-[13px] text-zinc-200 outline-none placeholder:text-zinc-600 focus:bg-zinc-800 focus:ring-1 focus:ring-zinc-600"
            />
          </div>
        </div>

        <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Previous page">
          <ChevronLeft size={16} />
        </button>
        <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Next page">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Category tabs */}
      <div className="flex items-center border-b border-zinc-800/60">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={clsx(
              'relative flex flex-1 items-center justify-center gap-1.5 px-4 py-3 text-[13px] font-medium transition-colors',
              activeTab === tab.id ? 'text-zinc-100' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.02]'
            )}
          >
            {tab.label}
            {tab.id === 'primary' && unreadCount > 0 && (
              <span className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold bg-blue-500/20 text-blue-400">
                {unreadCount}
              </span>
            )}
            {tab.id !== 'primary' && tab.badge && (
              <span className={clsx('rounded-full px-1.5 py-0.5 text-[10px] font-semibold', tab.badgeColor || 'bg-emerald-500/20 text-emerald-400')}>
                {tab.badge} new
              </span>
            )}
            {activeTab === tab.id && (
              <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-zinc-400" />
            )}
          </button>
        ))}
      </div>
    </>
  )
}

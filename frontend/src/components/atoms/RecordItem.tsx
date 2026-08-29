import { MoreHorizontal } from 'lucide-react'
import clsx from 'clsx'
import type { Record } from '../../lib/workspace/types'

type Props = {
  record: Record
  onSelect: () => void
  onMenuClick: (e: React.MouseEvent) => void
  onDragStart: (e: React.DragEvent) => void
  onContextMenu: (e: React.MouseEvent) => void
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  } else if (diffDays === 1) {
    return 'Yesterday'
  } else if (diffDays < 7) {
    return date.toLocaleDateString(undefined, { weekday: 'short' })
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function RecordItem({ record, onSelect, onMenuClick, onDragStart, onContextMenu }: Props) {
  const timeLabel = formatTime(record.updatedAt)

  const handleMenuClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onMenuClick(e)
  }

  return (
    <div
      role="button"
      tabIndex={0}
      draggable="true"
      onClick={onSelect}
      onDragStart={onDragStart}
      onContextMenu={onContextMenu}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onSelect()
      }}
      className={clsx(
        'group flex items-center gap-3 rounded-md px-2 py-2',
        'cursor-pointer transition-colors duration-150',
        'hover:bg-white/5',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
      )}
    >
      {/* Colored circle dot */}
      <span className="h-2 w-2 shrink-0 rounded-full bg-[#3ecf8e]" />
      {/* Title and subtitle */}
      <div className="flex flex-1 flex-col min-w-0">
        <span className="truncate text-sm text-white">{record.title}</span>
        <span className="text-[11px] text-zinc-500">Record • {timeLabel}</span>
      </div>
      {/* Three-dot menu (visible on hover) */}
      <button
        type="button"
        onClick={handleMenuClick}
        aria-label={`Actions for ${record.title}`}
        className={clsx(
          'shrink-0 rounded p-1 text-zinc-600 opacity-0 transition-opacity duration-150',
          'group-hover:opacity-100',
          'hover:bg-white/10 hover:text-zinc-300',
          'focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
        )}
      >
        <MoreHorizontal size={14} />
      </button>
    </div>
  )
}

import { Calendar, StickyNote, Plus } from 'lucide-react'
import clsx from 'clsx'

/**
 * Gmail-style right sidebar rail — thin vertical strip with icon buttons.
 * The "+" icon triggers the chat panel.
 */

type RightRailProps = {
  onPlusClick: () => void
}

const RAIL_ITEMS = [
  { id: 'calendar', icon: <Calendar size={18} />, label: 'Calendar' },
  { id: 'notes', icon: <StickyNote size={18} />, label: 'Notes' },
]

export function RightRail({ onPlusClick }: RightRailProps) {
  return (
    <aside
      className="hidden md:flex h-full w-[52px] flex-col items-center border-l border-zinc-800/60 bg-[#0f0f0f] py-3 gap-2"
      aria-label="Side panel"
    >
      {RAIL_ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
          aria-label={item.label}
          title={item.label}
        >
          {item.icon}
        </button>
      ))}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Plus button — opens chat */}
      <button
        type="button"
        onClick={onPlusClick}
        className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
        aria-label="Open chat"
        title="Open chat"
      >
        <Plus size={20} />
      </button>
    </aside>
  )
}

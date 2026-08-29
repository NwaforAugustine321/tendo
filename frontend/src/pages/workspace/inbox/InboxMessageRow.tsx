import { Trash2, Clock, Star } from 'lucide-react'
import clsx from 'clsx'
import type { InboxMessage } from './types'

type Props = {
  msg: InboxMessage
  selected: boolean
  starred: boolean
  onSelect: () => void
  onStar: () => void
  onClick: () => void
  onDelete: () => void
}

export function InboxMessageRow({ msg, selected, starred, onSelect, onStar, onClick, onDelete }: Props) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'group flex items-center gap-0 border-b border-zinc-800/40 px-4 py-1.5 transition-colors cursor-pointer',
        !msg.read ? 'bg-zinc-900/50' : 'bg-transparent',
        selected && 'bg-emerald-500/5',
        'hover:bg-white/[0.03] hover:shadow-[inset_2px_0_0_0_#3ecf8e]'
      )}
    >
      {/* Checkbox */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onSelect() }}
        className={clsx(
          'flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors mr-2',
          selected ? 'border-emerald-500 bg-emerald-500' : 'border-zinc-700 hover:border-zinc-500'
        )}
        aria-label={`Select message from ${msg.sender}`}
      >
        {selected && (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        )}
      </button>

      {/* Star */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onStar() }}
        className={clsx(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors mr-2',
          starred ? 'text-yellow-400' : 'text-zinc-600 hover:text-zinc-400'
        )}
        aria-label={starred ? 'Unstar' : 'Star'}
      >
        <Star size={16} fill={starred ? 'currentColor' : 'none'} />
      </button>

      {/* Sender */}
      <span className={clsx('w-[160px] shrink-0 truncate text-[13px]', !msg.read ? 'font-medium text-zinc-100' : 'text-zinc-400')}>
        {msg.sender}
      </span>

      {/* Subject + preview */}
      <div className="min-w-0 flex-1 flex items-baseline gap-1 mr-3">
        <span className={clsx('shrink-0 truncate text-[13px]', !msg.read ? 'text-zinc-100' : 'text-zinc-400')}>
          {msg.subject}
        </span>
        <span className="text-zinc-600 text-[13px] shrink-0">-</span>
        <span className="min-w-0 truncate text-[13px] text-zinc-500">{msg.preview}</span>
      </div>

      {/* Hover actions */}
      <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex mr-2">
        <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Delete" onClick={(e) => { e.stopPropagation(); onDelete() }}>
          <Trash2 size={15} />
        </button>
        <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Snooze" onClick={(e) => e.stopPropagation()}>
          <Clock size={15} />
        </button>
      </div>

      {/* Date */}
      <span className={clsx('shrink-0 text-[12px] tabular-nums', !msg.read ? 'text-zinc-200' : 'text-zinc-500')}>
        {msg.date}
      </span>
    </div>
  )
}

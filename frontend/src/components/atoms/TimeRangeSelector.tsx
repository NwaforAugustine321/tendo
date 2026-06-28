import clsx from 'clsx'
import type { TimeRange } from '../../lib/workspace/dashboard-types'

type Props = {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

const options: { label: string; value: TimeRange }[] = [
  { label: 'Today', value: 'today' },
  { label: 'Yesterday', value: 'yesterday' },
  { label: '7D', value: '7d' },
  { label: '30D', value: '30d' },
]

export function TimeRangeSelector({ value, onChange }: Props) {
  return (
    <div className="flex items-center gap-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={clsx(
            'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
            value === opt.value
              ? 'bg-zinc-800 text-zinc-100 border-zinc-600'
              : 'text-zinc-400 hover:text-zinc-300 border-zinc-800/50 hover:border-zinc-700'
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

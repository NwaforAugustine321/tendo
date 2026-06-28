import type { TimeRange } from '../../lib/workspace/dashboard-types'
import { getGreeting } from '../../lib/workspace/dashboard-utils'
import { TimeRangeSelector } from '../atoms'

type Props = {
  name: string
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
}

export function GreetingHeader({ name, timeRange, onTimeRangeChange }: Props) {
  const greeting = getGreeting(new Date().getHours())

  return (
    <div className="flex items-center justify-between px-6 py-4">
      {/* Left side */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-bold text-white">
          {greeting}, {name} 👋
        </h1>
        <p className="text-sm text-zinc-400">
          Here&apos;s what&apos;s happening in your business today.
        </p>
        <span className="mt-1 inline-flex w-fit items-center gap-1.5 rounded-full bg-zinc-800/60 border border-zinc-700/50 px-3 py-1 text-[11px] font-medium text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Business is healthy · Compared to yesterday
        </span>
      </div>

      {/* Right side */}
      <TimeRangeSelector value={timeRange} onChange={onTimeRangeChange} />
    </div>
  )
}

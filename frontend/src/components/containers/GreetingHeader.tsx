import { getGreeting } from '../../lib/workspace/dashboard-utils'
import type { SnapshotRecommendation } from '../../lib/services/snapshot'

type Props = {
  name: string
  recommendations?: SnapshotRecommendation[]
}

function getHealthStatus(recommendations: SnapshotRecommendation[]): { label: string; color: string; dot: string } {
  const high = recommendations.filter((r) => r.priority === 'high').length
  const medium = recommendations.filter((r) => r.priority === 'medium').length

  if (high >= 3) return { label: 'Needs urgent attention', color: 'text-red-400', dot: 'bg-red-400' }
  if (high >= 1) return { label: 'Some issues need attention', color: 'text-amber-400', dot: 'bg-amber-400' }
  if (medium >= 3) return { label: 'Mostly healthy · A few things to watch', color: 'text-amber-400', dot: 'bg-amber-400' }
  return { label: 'Business is healthy', color: 'text-emerald-400', dot: 'bg-emerald-400' }
}

export function GreetingHeader({ name, recommendations = [] }: Props) {
  const greeting = getGreeting(new Date().getHours())
  const health = getHealthStatus(recommendations)

  const high = recommendations.filter((r) => r.priority === 'high').length
  const medium = recommendations.filter((r) => r.priority === 'medium').length
  const low = recommendations.filter((r) => r.priority === 'low').length

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
        <span className="mt-1 inline-flex w-fit items-center gap-1.5 rounded-full bg-zinc-800/60 border border-zinc-700/50 px-3 py-1 text-[11px] font-medium">
          <span className={`h-1.5 w-1.5 rounded-full ${health.dot}`} />
          <span className={health.color}>{health.label}</span>
        </span>
      </div>

      {/* Right side — recommendation priority counts */}
      <div className="flex items-center gap-3">
        {high > 0 && (
          <div className="flex items-center gap-1.5 rounded-full bg-red-950/30 border border-red-800/30 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
            <span className="text-[11px] font-medium text-red-400">{high} high</span>
          </div>
        )}
        {medium > 0 && (
          <div className="flex items-center gap-1.5 rounded-full bg-amber-950/30 border border-amber-800/30 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            <span className="text-[11px] font-medium text-amber-400">{medium} medium</span>
          </div>
        )}
        {low > 0 && (
          <div className="flex items-center gap-1.5 rounded-full bg-zinc-800/50 border border-zinc-700/30 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-400" />
            <span className="text-[11px] font-medium text-zinc-400">{low} low</span>
          </div>
        )}
        {recommendations.length === 0 && (
          <span className="text-[11px] text-zinc-500">No recommendations yet</span>
        )}
      </div>
    </div>
  )
}

type Change = {
  label: string
  before: string
  after: string
}

type Props = {
  operationType: string
  changes: Change[]
  onRevert?: () => void
  onContinueFromHere?: () => void
}

export function OperationCard({ operationType, changes, onRevert, onContinueFromHere }: Props) {
  return (
    <div className="av-card-interactive border-l-2 border-l-[#3ecf8e]">
      <div className="flex items-center gap-2 mb-3">
        <span className="h-2 w-2 rounded-full bg-[#3ecf8e]" />
        <p className="text-xs font-semibold text-[#3ecf8e]">{operationType} ✓</p>
      </div>

      <div className="space-y-1.5 mb-4">
        {changes.map((c, i) => (
          <div key={i} className="flex items-baseline justify-between text-xs">
            <span className="text-zinc-400">{c.label}</span>
            <span className="text-zinc-300">
              <span className="text-zinc-400">{c.before}</span>
              <span className="mx-1 text-zinc-400">→</span>
              <span className="font-medium text-white">{c.after}</span>
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {onRevert && (
          <button type="button" className="av-btn-toolbar-secondary" onClick={onRevert}>
            ↩ Revert Change
          </button>
        )}
        {onContinueFromHere && (
          <button type="button" className="av-btn-toolbar-secondary" onClick={onContinueFromHere}>
            ▶ Continue From Here
          </button>
        )}
      </div>
    </div>
  )
}

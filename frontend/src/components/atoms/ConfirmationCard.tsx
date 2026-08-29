type Props = {
  summary: string
  details: { label: string; value: string }[]
  onConfirm: () => void
  onModify: () => void
  onCancel: () => void
}

export function ConfirmationCard({ summary, details, onConfirm, onModify, onCancel }: Props) {
  return (
    <div className="av-card-interactive border-l-2 border-l-amber-400">
      <p className="av-kicker mb-3 text-amber-400">Confirm Operation</p>
      <p className="mb-3 text-sm text-zinc-200">{summary}</p>

      {details.length > 0 && (
        <div className="mb-4 space-y-1.5">
          {details.map((d, i) => (
            <div key={i} className="flex items-baseline justify-between text-xs">
              <span className="text-zinc-400">{d.label}</span>
              <span className="font-medium text-zinc-200">{d.value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button type="button" className="av-btn-primary" onClick={onConfirm}>
          ✓ Confirm
        </button>
        <button type="button" className="av-btn-secondary" onClick={onModify}>
          ✏ Modify
        </button>
        <button type="button" className="av-btn-secondary" onClick={onCancel}>
          ✕ Cancel
        </button>
      </div>
    </div>
  )
}

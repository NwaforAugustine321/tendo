type Choice = {
  id: string
  label: string
  recommended?: boolean
}

type Props = {
  prompt: string
  choices: Choice[]
  onSelect: (id: string) => void
}

export function OptionCard({ prompt, choices, onSelect }: Props) {
  return (
    <div className="av-dashboard-surface">
      <p className="mb-3 text-sm text-zinc-200">{prompt}</p>
      <div className="flex flex-wrap gap-2">
        {choices.map((choice) => (
          <button
            key={choice.id}
            type="button"
            className={choice.recommended ? 'av-btn-primary' : 'av-btn-secondary'}
            onClick={() => onSelect(choice.id)}
          >
            {choice.label}
          </button>
        ))}
      </div>
    </div>
  )
}

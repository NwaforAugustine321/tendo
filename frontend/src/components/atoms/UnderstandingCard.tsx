type Props = {
  title?: string
  businessName?: string
  activities?: string[]
  behaviors?: string[]
  note?: string
}

export function UnderstandingCard({
  title = 'My Understanding',
  businessName,
  activities = [],
  behaviors = [],
  note = 'This is my initial understanding and I will continue learning how your business operates.',
}: Props) {
  return (
    <div className="av-card-interactive border-l-2 border-l-[#3ecf8e]">
      <p className="av-kicker mb-3">{title}</p>

      <div className="space-y-3">
        {businessName && (
          <div>
            <p className="text-xs font-semibold text-zinc-400">Business Name</p>
            <p className="mt-0.5 text-sm font-medium text-white">{businessName}</p>
          </div>
        )}

        {activities.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-zinc-400">Business Activities</p>
            <ul className="mt-1 space-y-1">
              {activities.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-zinc-200">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#3ecf8e]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {behaviors.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-zinc-400">Business Behaviors</p>
            <ul className="mt-1 space-y-1">
              {behaviors.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-zinc-200">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#3ecf8e]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {note && (
          <p className="mt-2 text-xs italic text-zinc-400">{note}</p>
        )}
      </div>
    </div>
  )
}

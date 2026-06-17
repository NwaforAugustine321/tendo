/**
 * Empty state — shown when conversation has no messages yet.
 */
export function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-16">
      {/* Tendo icon */}
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
        <span className="flex items-center gap-[4px]">
          <span className="h-[8px] w-[8px] rounded-full bg-purple-600" />
          <span className="h-[8px] w-[8px] rounded-full bg-purple-600" />
        </span>
      </div>

      <h2 className="mt-5 text-lg font-semibold tracking-tight text-white">
        How can I help you today?
      </h2>
      <p className="mt-2 max-w-xs text-center text-sm text-zinc-500">
        Talk to me about your business. I can record sales, track inventory, manage payments, and more.
      </p>

      {/* Suggestion chips */}
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <Chip icon="📦" label="Record a sale" />
        <Chip icon="💰" label="Check customer debt" />
        <Chip icon="📊" label="Today's summary" />
        <Chip icon="🎤" label="Use voice" />
      </div>
    </div>
  )
}

function Chip({ icon, label }: { icon: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-800/90 bg-[#141414] px-3 py-1.5 text-xs text-zinc-400">
      <span>{icon}</span>
      <span>{label}</span>
    </span>
  )
}

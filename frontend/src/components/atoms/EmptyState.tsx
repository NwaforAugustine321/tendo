import { Package, Wallet, BarChart3, Mic } from 'lucide-react'

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

      {/* Suggestion chips with colored accents */}
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <Chip icon={<Package size={14} />} label="Record a sale" color="orange" />
        <Chip icon={<Wallet size={14} />} label="Check debt" color="red" />
        <Chip icon={<BarChart3 size={14} />} label="Today's summary" color="green" />
        <Chip icon={<Mic size={14} />} label="Use voice" color="green" />
      </div>
    </div>
  )
}

type ChipColor = 'orange' | 'red' | 'green'

function Chip({ icon, label, color }: { icon: React.ReactNode; label: string; color: ChipColor }) {
  const colorClasses: Record<ChipColor, string> = {
    orange: 'border-orange-500/30 text-orange-400',
    red: 'border-red-500/30 text-red-400',
    green: 'border-[#3ecf8e]/30 text-[#3ecf8e]',
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border bg-[#141414] px-3 py-1.5 text-xs ${colorClasses[color]}`}>
      <span>{icon}</span>
      <span>{label}</span>
    </span>
  )
}

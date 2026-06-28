import { Mic, AudioLines } from 'lucide-react'

type Props = {
  onMicClick?: () => void
}

export function CentralHub({ onMicClick }: Props) {
  return (
    <button
      type="button"
      onClick={onMicClick}
      className="relative flex flex-col items-center justify-center aspect-square w-[clamp(160px,18vw,240px)] rounded-full focus:outline-none"
    >
      {/* Outermost green glow ring */}
      <div className="absolute inset-0 rounded-full border border-emerald-500/30 shadow-[0_0_40px_rgba(16,185,129,0.12)]" />
      {/* Second ring */}
      <div className="absolute inset-[8%] rounded-full border border-emerald-600/20" />
      {/* Third dark ring */}
      <div className="absolute inset-[18%] rounded-full border border-zinc-700/30 bg-[#0d0d0d]" />
      {/* Inner dark filled circle */}
      <div className="absolute inset-[28%] rounded-full bg-[#0a0a0a] border border-zinc-800/40" />

      {/* Center content */}
      <div className="relative z-10 flex flex-col items-center gap-1">
        <div className="flex items-center justify-center">
          <Mic size={20} className="text-emerald-400" />
        </div>
        <span className="text-sm font-medium text-white mt-1">Ask Tendo AI</span>
        <span className="text-[10px] text-zinc-500 text-center leading-tight">
          Ask anything about your<br />business
        </span>
        <AudioLines size={14} className="text-emerald-600/50 mt-0.5" />
      </div>
    </button>
  )
}

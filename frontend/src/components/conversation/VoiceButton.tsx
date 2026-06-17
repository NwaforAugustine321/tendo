import { Mic } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  onRecorded?: (blob: Blob) => void
  onToggle?: () => void
  isListening?: boolean
}

export function VoiceButton({ onToggle, isListening = false }: Props) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onToggle}
        className={clsx(
          'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200',
          isListening
            ? 'animate-pulse border-red-400 bg-red-500/10 text-red-400'
            : 'border-[#3ecf8e]/50 text-[#3ecf8e] hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10'
        )}
        aria-label={isListening ? 'Stop recording' : 'Start voice recording'}
      >
        <Mic size={18} />
        {isListening && (
          <span className="absolute inset-0 animate-ping rounded-full border border-red-400/30" />
        )}
      </button>

      {isListening && (
        <span className="text-xs text-red-400">Listening...</span>
      )}
    </div>
  )
}

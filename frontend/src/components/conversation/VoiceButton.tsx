import clsx from 'clsx'

type Props = {
  /** Legacy: callback for recorded audio blob */
  onRecorded?: (blob: Blob) => void
  /** Live streaming: toggle mic on/off via WebSocket */
  onToggle?: () => void
  /** Whether currently streaming mic audio */
  isListening?: boolean
}

export function VoiceButton({ onToggle, isListening = false }: Props) {
  const handleClick = () => {
    onToggle?.()
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        className={clsx(
          'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200',
          isListening
            ? 'animate-pulse border-red-400 bg-red-500/10 text-red-400'
            : 'border-[#3ecf8e]/50 text-[#3ecf8e] hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10'
        )}
        aria-label={isListening ? 'Stop recording' : 'Start voice recording'}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4Z"
            stroke="currentColor"
            strokeWidth="2"
          />
          <path
            d="M19 10v1a7 7 0 0 1-14 0v-1M12 19v4M8 23h8"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

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

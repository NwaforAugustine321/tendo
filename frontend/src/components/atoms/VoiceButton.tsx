import { useEffect, useRef, useState } from 'react'
import { Mic } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  onRecorded?: (blob: Blob) => void
  onToggle?: () => void
  isListening?: boolean
  loading?: boolean
}

export function VoiceButton({ onToggle, isListening = false, loading = false }: Props) {
  const [duration, setDuration] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (isListening) {
      setDuration(0)
      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1)
      }, 1000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setDuration(0)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isListening])

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onToggle}
        disabled={loading}
        className={clsx(
          'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200',
          loading
            ? 'border-zinc-500 text-zinc-400 cursor-wait'
            : isListening
              ? 'border-red-400 bg-red-500/10 text-red-400'
              : 'border-[#3ecf8e]/50 text-[#3ecf8e] hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10'
        )}
        aria-label={loading ? 'Connecting...' : isListening ? 'Stop recording' : 'Start voice recording'}
      >
        {loading ? (
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <Mic size={18} />
        )}
        {isListening && !loading && (
          <span className="absolute inset-0 animate-ping rounded-full border border-red-400/30" />
        )}
      </button>

      {isListening && !loading && (
        <span className="text-xs tabular-nums text-red-400">
          {formatTime(duration)}
        </span>
      )}
    </div>
  )
}

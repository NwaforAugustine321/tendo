import { useEffect, useRef, useState } from 'react'
import { Mic } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  onRecorded?: (blob: Blob) => void
  onToggle?: () => void
  isListening?: boolean
}

export function VoiceButton({ onToggle, isListening = false }: Props) {
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
        className={clsx(
          'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200',
          isListening
            ? 'border-red-400 bg-red-500/10 text-red-400'
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
        <span className="text-xs tabular-nums text-red-400">
          {formatTime(duration)}
        </span>
      )}
    </div>
  )
}

import { useState, useRef, useCallback } from 'react'
import clsx from 'clsx'

type Props = {
  onRecorded: (blob: Blob) => void
}

export function VoiceButton({ onRecorded }: Props) {
  const [state, setState] = useState<'idle' | 'recording' | 'processing'>('idle')
  const [duration, setDuration] = useState(0)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorder.current = recorder
      chunks.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        stream.getTracks().forEach((t) => t.stop())
        setState('processing')
        setTimeout(() => {
          onRecorded(blob)
          setState('idle')
          setDuration(0)
        }, 500)
      }

      recorder.start()
      setState('recording')
      setDuration(0)
      timerRef.current = setInterval(() => {
        setDuration((d) => {
          if (d >= 120) {
            stopRecording()
            return d
          }
          return d + 1
        })
      }, 1000)
    } catch {
      setState('idle')
    }
  }, [onRecorded])

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop()
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const handleClick = () => {
    if (state === 'idle') startRecording()
    else if (state === 'recording') stopRecording()
  }

  const formatDuration = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={state === 'processing'}
        className={clsx(
          'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200',
          state === 'idle' &&
            'border-[#3ecf8e]/50 text-[#3ecf8e] hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10',
          state === 'recording' &&
            'animate-pulse border-red-400 bg-red-500/10 text-red-400',
          state === 'processing' &&
            'border-zinc-600 text-zinc-500'
        )}
        aria-label={state === 'recording' ? 'Stop recording' : 'Start voice recording'}
      >
        {state === 'processing' ? (
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : (
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
        )}

        {state === 'recording' && (
          <span className="absolute inset-0 animate-ping rounded-full border border-red-400/30" />
        )}
      </button>

      {state === 'recording' && (
        <span className="text-xs tabular-nums text-red-400">
          {formatDuration(duration)}
        </span>
      )}
    </div>
  )
}

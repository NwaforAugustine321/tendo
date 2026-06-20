import { useState, useRef, useEffect } from 'react'
import { Play, Pause } from 'lucide-react'
import clsx from 'clsx'
import { BotAvatar } from './BotAvatar'
import { UserAvatar } from './UserAvatar'

type Props = {
  role: 'user' | 'assistant'
  content: string
  audioUrl?: string
}

function VoiceWaveform({ audioUrl }: { audioUrl?: string }) {
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [waveform, setWaveform] = useState<number[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const animRef = useRef<number | null>(null)
  const playingRef = useRef(false)

  const NUM_BARS = 30

  useEffect(() => {
    if (!audioUrl) return

    const ctx = new AudioContext()
    fetch(audioUrl)
      .then((res) => res.arrayBuffer())
      .then((buf) => ctx.decodeAudioData(buf))
      .then((decoded) => {
        const raw = decoded.getChannelData(0)
        const step = Math.floor(raw.length / NUM_BARS)
        const bars: number[] = []
        for (let i = 0; i < NUM_BARS; i++) {
          let sum = 0
          for (let j = 0; j < step; j++) {
            sum += Math.abs(raw[i * step + j])
          }
          bars.push(sum / step)
        }
        // Normalize to 4–14px range
        const max = Math.max(...bars, 0.01)
        setWaveform(bars.map((v) => 4 + (v / max) * 10))
        ctx.close()
      })
      .catch(() => {
        // Fallback static bars
        setWaveform(Array.from({ length: NUM_BARS }, () => 4 + Math.random() * 8))
      })
  }, [audioUrl])

  const tick = () => {
    if (audioRef.current && audioRef.current.duration) {
      setProgress(audioRef.current.currentTime / audioRef.current.duration)
    }
    if (playingRef.current) {
      animRef.current = requestAnimationFrame(tick)
    }
  }

  const togglePlay = () => {
    if (!audioUrl) return

    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl)
      audioRef.current.onended = () => {
        playingRef.current = false
        setPlaying(false)
        setProgress(0)
        if (animRef.current) cancelAnimationFrame(animRef.current)
      }
    }

    if (playing) {
      audioRef.current.pause()
      playingRef.current = false
      setPlaying(false)
      if (animRef.current) cancelAnimationFrame(animRef.current)
    } else {
      audioRef.current.play()
      playingRef.current = true
      setPlaying(true)
      animRef.current = requestAnimationFrame(tick)
    }
  }

  const activeBars = Math.floor(progress * waveform.length)

  return (
    <div className="flex items-center gap-1.5 py-0.5">
      <button
        type="button"
        onClick={togglePlay}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#3ecf8e] text-[#0a0a0a] transition hover:bg-[#4ddb9b]"
        aria-label={playing ? 'Pause' : 'Play'}
      >
        {playing ? <Pause size={12} fill="currentColor" /> : <Play size={12} fill="currentColor" />}
      </button>
      <div className="flex items-end gap-[2px]" style={{ height: 16 }}>
        {waveform.map((h, i) => (
          <span
            key={i}
            className="inline-block w-[2px] rounded-full transition-colors duration-75"
            style={{
              height: `${h}px`,
              backgroundColor: i < activeBars ? '#3ecf8e' : '#52525b',
            }}
          />
        ))}
      </div>
    </div>
  )
}

export function MessageBubble({ role, content, audioUrl }: Props) {
  const isUser = role === 'user'
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const isVoice = content === '🎤 Voice message'

  return (
    <div className={clsx('flex gap-2', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {!isUser ? <BotAvatar size={28} /> : <UserAvatar size={28} />}

      <div className="relative max-w-[80%]">
        {/* Tail */}
        <div
          className={clsx(
            'absolute top-2 h-3 w-3 rotate-45',
            isUser
              ? '-right-1.5 bg-[#1a2e1a]'
              : '-left-1.5 border border-zinc-800/90 bg-[#141414]'
          )}
        />

        {/* Body */}
        <div
          className={clsx(
            'relative rounded-lg px-3 py-1.5 text-[13px] leading-snug',
            isUser
              ? 'bg-[#1a2e1a] text-zinc-100'
              : 'border border-zinc-800/90 bg-[#141414] text-zinc-200'
          )}
        >
          {isVoice ? (
            <VoiceWaveform audioUrl={audioUrl} />
          ) : (
            content.split('\n').map((line, i) => (
              <p key={i} className={i > 0 ? 'mt-0.5' : ''}>
                {line}
              </p>
            ))
          )}

          <span className={clsx(
            'mt-0.5 block text-right text-[10px]',
            isUser ? 'text-zinc-400' : 'text-zinc-400'
          )}>
            {time}
          </span>
        </div>
      </div>
    </div>
  )
}

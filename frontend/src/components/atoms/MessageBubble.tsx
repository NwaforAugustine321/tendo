import { useState, useRef } from 'react'
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
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const bars = [3, 6, 4, 8, 5, 10, 7, 4, 9, 6, 3, 7, 5, 8, 4, 6, 9, 5, 3, 7, 6, 4, 8, 5, 3]

  const togglePlay = () => {
    if (!audioUrl) return

    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl)
      audioRef.current.onended = () => setPlaying(false)
    }

    if (playing) {
      audioRef.current.pause()
      setPlaying(false)
    } else {
      audioRef.current.play()
      setPlaying(true)
    }
  }

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
      <div className="flex items-center gap-[2px]">
        {bars.map((h, i) => (
          <span
            key={i}
            className={clsx(
              'inline-block w-[2.5px] rounded-full transition-colors',
              playing ? 'bg-[#3ecf8e]' : 'bg-zinc-600'
            )}
            style={{ height: `${h}px` }}
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
            isUser ? 'text-zinc-500' : 'text-zinc-600'
          )}>
            {time}
          </span>
        </div>
      </div>
    </div>
  )
}

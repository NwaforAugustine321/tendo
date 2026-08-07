import { useEffect, useState } from 'react'

type Props = {
  active: boolean
  speaking: boolean
}

export function SpeakingIndicator({ active, speaking }: Props) {
  const [bars, setBars] = useState([0.3, 0.5, 0.7, 0.4, 0.6])

  useEffect(() => {
    if (!active) return

    const interval = setInterval(() => {
      if (speaking) {
        setBars(prev => prev.map(() => 0.3 + Math.random() * 0.7))
      } else {
        setBars(prev => prev.map((v) => 0.2 + Math.sin(Date.now() / 600 + prev.indexOf(v)) * 0.15))
      }
    }, speaking ? 100 : 400)

    return () => clearInterval(interval)
  }, [active, speaking])

  if (!active) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex items-center gap-2 rounded-full bg-zinc-900/90 px-3 py-2 shadow-lg backdrop-blur-sm border border-zinc-700/50">
      <div className="relative flex items-center justify-center">
        {/* Pulsing ring */}
        <div className={`absolute w-8 h-8 rounded-full border ${speaking ? 'border-emerald-400/60 animate-ping' : 'border-zinc-500/30 animate-pulse'}`} style={{ animationDuration: speaking ? '1.2s' : '3s' }} />
        {/* Bars */}
        <div className="relative flex items-end gap-[2px] h-4 z-10">
          {bars.map((height, i) => (
            <div
              key={i}
              className={`w-[3px] rounded-full transition-all ${speaking ? 'bg-emerald-400' : 'bg-zinc-400'}`}
              style={{
                height: `${height * 100}%`,
                transitionDuration: speaking ? '80ms' : '300ms',
              }}
            />
          ))}
        </div>
      </div>
      <span className={`text-xs font-medium ${speaking ? 'text-emerald-300' : 'text-zinc-400'}`}>
        {speaking ? 'Speaking' : 'Listening'}
      </span>
    </div>
  )
}

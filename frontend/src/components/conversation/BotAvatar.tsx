import { useEffect, useState } from 'react'

/**
 * Tendo bot avatar — white circle with two purple eyes that blink.
 * Inspired by the Kiro IDE bot avatar style.
 */
export function BotAvatar({ size = 32 }: { size?: number }) {
  const [blinking, setBlinking] = useState(false)

  useEffect(() => {
    const blink = () => {
      setBlinking(true)
      setTimeout(() => setBlinking(false), 150)
    }

    const schedule = () => {
      const delay = 2000 + Math.random() * 3000
      return setTimeout(() => {
        blink()
        timerId = schedule()
      }, delay)
    }

    let timerId = schedule()
    return () => clearTimeout(timerId)
  }, [])

  const eyeSize = size * 0.24
  const eyeGap = size * 0.12

  return (
    <div
      className="relative shrink-0 rounded-full bg-white border-2 border-zinc-900 flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* Two purple eyes */}
      <div className="flex items-center" style={{ gap: eyeGap }}>
        <span
          className="rounded-full bg-purple-600 transition-transform duration-100"
          style={{
            width: eyeSize,
            height: blinking ? 2 : eyeSize,
            transform: blinking ? 'scaleY(0.15)' : 'scaleY(1)',
          }}
        />
        <span
          className="rounded-full bg-purple-600 transition-transform duration-100"
          style={{
            width: eyeSize,
            height: blinking ? 2 : eyeSize,
            transform: blinking ? 'scaleY(0.15)' : 'scaleY(1)',
          }}
        />
      </div>
    </div>
  )
}

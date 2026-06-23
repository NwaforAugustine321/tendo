import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

type Props = {
  text?: string
  thoughtText?: string
}

export function TypingIndicator({ text, thoughtText }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [displayedThought, setDisplayedThought] = useState('')
  const streamIndex = useRef(0)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Auto-open when new thought arrives, reset when cleared
  useEffect(() => {
    if (thoughtText) {
      setExpanded(true)
      setDisplayedThought('')
      streamIndex.current = 0

      // Stream text character by character
      intervalRef.current = setInterval(() => {
        streamIndex.current += 1
        if (streamIndex.current >= (thoughtText?.length || 0)) {
          if (intervalRef.current) clearInterval(intervalRef.current)
          setDisplayedThought(thoughtText || '')
        } else {
          setDisplayedThought(thoughtText!.slice(0, streamIndex.current))
        }
      }, 15)
    } else {
      // Reset and close when thought is cleared (done or error)
      setExpanded(false)
      setDisplayedThought('')
      streamIndex.current = 0
      if (intervalRef.current) clearInterval(intervalRef.current)
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [thoughtText])

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex items-center gap-2 rounded-2xl border border-zinc-800/90 bg-[#141414] px-4 py-2.5">
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
        </span>
        {text && <span className="text-xs text-zinc-400">{text}</span>}
        {thoughtText && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-1 text-zinc-500 hover:text-zinc-300 transition-colors"
            aria-label={expanded ? 'Hide thought' : 'Show thought'}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>
      {thoughtText && expanded && (
        <div className="ml-2 max-w-[85%] rounded-xl border border-zinc-800/60 bg-zinc-900/50 px-3 py-2 text-[11px] text-zinc-500 italic leading-relaxed">
          {displayedThought}
          {displayedThought.length < (thoughtText?.length || 0) && (
            <span className="animate-pulse">▊</span>
          )}
        </div>
      )}
    </div>
  )
}

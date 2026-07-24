import { useState, useRef, useCallback, useEffect } from 'react'
import { Minimize2, Maximize2, X, GripHorizontal } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  children: React.ReactNode
  title?: string
  visible: boolean
  onClose: () => void
  defaultWidth?: number
  defaultHeight?: number
  offsetIndex?: number
}

export function FloatingPanel({
  children,
  title = 'Chat',
  visible,
  onClose,
  defaultWidth = 600,
  defaultHeight = 420,
  offsetIndex = 0,
}: Props) {
  const [minimized, setMinimized] = useState(false)
  const [position, setPosition] = useState({ x: window.innerWidth - defaultWidth - 24 - (offsetIndex * 30), y: window.innerHeight - defaultHeight - 80 + (offsetIndex * 30) })
  const [dragging, setDragging] = useState(false)
  const dragOffset = useRef({ x: 0, y: 0 })
  const panelRef = useRef<HTMLDivElement>(null)

  // Allow panel to be dragged freely — only keep at least 48px visible on any edge
  const clampPosition = useCallback((x: number, y: number) => {
    const w = minimized ? 200 : defaultWidth
    const h = minimized ? 48 : defaultHeight
    return {
      x: Math.max(-w + 48, Math.min(x, window.innerWidth - 48)),
      y: Math.max(-h + 48, Math.min(y, window.innerHeight - 48)),
    }
  }, [minimized, defaultWidth, defaultHeight])

  // Mouse drag handlers
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDragging(true)
    const rect = panelRef.current?.getBoundingClientRect()
    if (rect) {
      dragOffset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top }
    }
  }, [])

  useEffect(() => {
    if (!dragging) return

    const onMouseMove = (e: MouseEvent) => {
      const newX = e.clientX - dragOffset.current.x
      const newY = e.clientY - dragOffset.current.y
      setPosition(clampPosition(newX, newY))
    }

    const onMouseUp = () => setDragging(false)

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [dragging, clampPosition])

  // Re-clamp on window resize
  useEffect(() => {
    const onResize = () => {
      setPosition((prev) => clampPosition(prev.x, prev.y))
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [clampPosition])

  if (!visible) return null

  return (
    <div
      ref={panelRef}
      className={clsx(
        'fixed z-50 rounded-xl border border-zinc-700/50 bg-[#0f0f0f] shadow-2xl shadow-black/50 transition-[width,height] duration-200 overflow-hidden flex flex-col',
        dragging && 'cursor-grabbing select-none'
      )}
      style={{
        left: position.x,
        top: position.y,
        width: minimized ? 200 : defaultWidth,
        height: minimized ? 48 : defaultHeight,
      }}
    >
      {/* Drag handle / title bar */}
      <div
        onMouseDown={onMouseDown}
        className="flex items-center justify-between px-3 py-2 bg-[#0a0a0a] border-b border-zinc-800/50 cursor-grab active:cursor-grabbing shrink-0"
      >
        <div className="flex items-center gap-2">
          <GripHorizontal size={12} className="text-zinc-600" />
          <span className="text-[11px] font-medium text-zinc-300">{title}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setMinimized(!minimized)}
            className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title={minimized ? 'Expand' : 'Minimize'}
          >
            {minimized ? <Maximize2 size={11} /> : <Minimize2 size={11} />}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors"
            title="Close"
          >
            <X size={11} />
          </button>
        </div>
      </div>

      {/* Content */}
      {!minimized && (
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
          {children}
        </div>
      )}
    </div>
  )
}

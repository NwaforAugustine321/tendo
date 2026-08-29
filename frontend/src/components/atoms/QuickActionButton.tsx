import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  onClick: () => void
  visible: boolean
  sidebarOpen?: boolean
}

export function QuickActionButton({ onClick, visible, sidebarOpen = true }: Props) {
  const [railHovered, setRailHovered] = useState(false)

  useEffect(() => {
    const onRailEnter = () => setRailHovered(true)
    const onRailLeave = () => setRailHovered(false)
    window.addEventListener('tendo:rail-enter', onRailEnter)
    window.addEventListener('tendo:rail-leave', onRailLeave)
    return () => {
      window.removeEventListener('tendo:rail-enter', onRailEnter)
      window.removeEventListener('tendo:rail-leave', onRailLeave)
    }
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick()
    }
  }

  // Sidebar open: after full width (52 + 260 = 312, centered on edge)
  // Sidebar closed + rail hovered: shift past expanded rail (176px + gap)
  // Sidebar closed + rail not hovered: just past the 52px rail
  let leftPosition = '305px'
  if (!sidebarOpen) {
    leftPosition = railHovered ? '190px' : '68px'
  }

  return (
    <div
      className={clsx(
        'fixed bottom-10 z-50 hidden md:block',
        'transition-[left] duration-300 ease-in-out',
        visible
          ? 'scale-100 opacity-100'
          : 'pointer-events-none scale-75 opacity-0'
      )}
      style={{ left: leftPosition }}
    >
      <div
        className="absolute inset-[-12px] rounded-full border-[1.5px] border-dashed border-[#3ecf8e]/40"
        aria-hidden="true"
      />
      <button
        type="button"
        onClick={onClick}
        onKeyDown={handleKeyDown}
        aria-hidden={!visible}
        aria-label="Quick actions"
        className={clsx(
          'relative flex h-14 w-14 items-center justify-center rounded-full',
          'bg-[#3ecf8e] text-white',
          'shadow-[0_0_16px_rgba(62,207,142,0.4)]',
          'transition-all duration-200 ease-in-out',
          'hover:shadow-[0_0_24px_rgba(62,207,142,0.6)] hover:brightness-110',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a]',
          'min-h-[44px] min-w-[44px]'
        )}
        tabIndex={visible ? 0 : -1}
      >
        <Sparkles size={22} />
      </button>
    </div>
  )
}

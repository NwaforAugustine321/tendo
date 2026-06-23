import { Sparkles } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  onClick: () => void
  visible: boolean
}

export function QuickActionButton({ onClick, visible }: Props) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick()
    }
  }

  return (
    <div
      className={clsx(
        'absolute bottom-10 right-0 z-50 translate-x-1/2',
        'transition-all duration-300 ease-in-out',
        visible
          ? 'scale-100 opacity-100'
          : 'pointer-events-none scale-75 opacity-0'
      )}
    >
      {/* Dashed orbit ring */}
      <div
        className="absolute inset-[-12px] rounded-full border-[1.5px] border-dashed border-[#3ecf8e]/40"
        aria-hidden="true"
      />
      {/* Main button */}
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

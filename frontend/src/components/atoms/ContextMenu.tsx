import { useEffect, type ReactNode } from 'react'
import clsx from 'clsx'

type MenuItem = {
  label: string
  icon?: ReactNode
  onClick: () => void
  danger?: boolean
}

type Props = {
  position: { x: number; y: number }
  items: MenuItem[]
  onClose: () => void
}

export function ContextMenu({ position, items, onClose }: Props) {
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('[data-context-menu]')) {
        onClose()
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  return (
    <div
      data-context-menu
      role="menu"
      className={clsx(
        'fixed z-50 min-w-[150px] rounded-lg border border-white/10',
        'bg-[#1a1a1a] py-1 shadow-xl'
      )}
      style={{ left: position.x, top: position.y }}
    >
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          role="menuitem"
          onClick={() => {
            item.onClick()
            onClose()
          }}
          className={clsx(
            'flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors',
            'hover:bg-white/5',
            item.danger ? 'text-red-400 hover:text-red-300' : 'text-zinc-300 hover:text-white'
          )}
        >
          {item.icon && <span className="shrink-0">{item.icon}</span>}
          {item.label}
        </button>
      ))}
    </div>
  )
}

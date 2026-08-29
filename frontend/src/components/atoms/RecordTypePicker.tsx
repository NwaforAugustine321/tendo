import { useEffect, useState } from 'react'
import { Type, Image, Mic, FileText, Plus, Camera, AudioLines } from 'lucide-react'
import clsx from 'clsx'
import type { EntryType } from '../../lib/workspace/types'

const ENTRY_TYPES: { type: EntryType; label: string; icon: typeof Type }[] = [
  { type: 'text', label: 'Text', icon: Type },
  { type: 'image', label: 'Image', icon: Image },
  { type: 'audio', label: 'Audio', icon: Mic },
  { type: 'pdf', label: 'PDF', icon: FileText },
]

const MORE_TYPES: { type: EntryType; label: string; icon: typeof Type }[] = [
  { type: 'camera' as EntryType, label: 'Camera', icon: Camera },
  { type: 'voice' as EntryType, label: 'Voice', icon: AudioLines },
]

type Props = {
  onSelect: (type: EntryType) => void
  onClose: () => void
  position?: { x: number; y: number }
}

export function RecordTypePicker({ onSelect, onClose, position }: Props) {
  const [showMore, setShowMore] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('[data-record-type-picker]')) onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [onClose])

  return (
    <div
      data-record-type-picker
      className={clsx(
        'z-50 rounded-xl border border-white/10 bg-[#1a1a1a] p-3 shadow-xl',
        position ? 'fixed' : 'absolute bottom-full left-0 mb-2'
      )}
      style={position ? { left: position.x, top: position.y } : undefined}
    >
      <p className="mb-2 text-[11px] font-medium text-zinc-400">Choose input type</p>
      <div className="flex gap-3">
        {ENTRY_TYPES.map(({ type, label, icon: Icon }) => (
          <button
            key={type}
            type="button"
            onClick={() => onSelect(type)}
            className={clsx(
              'flex flex-col items-center gap-1.5 rounded-lg px-3 py-2.5',
              'border border-white/10 transition-all duration-150',
              'hover:border-[#3ecf8e]/40 hover:bg-[#3ecf8e]/5',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
            )}
          >
            <Icon size={20} className="text-zinc-300" />
            <span className="text-[10px] font-medium text-zinc-400">{label}</span>
          </button>
        ))}
        {/* More button */}
        <button
          type="button"
          onClick={() => setShowMore(!showMore)}
          className={clsx(
            'flex flex-col items-center gap-1.5 rounded-lg px-3 py-2.5',
            'border transition-all duration-150',
            showMore
              ? 'border-[#3ecf8e]/40 bg-[#3ecf8e]/5'
              : 'border-white/10 hover:border-[#3ecf8e]/40 hover:bg-[#3ecf8e]/5',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
          )}
        >
          <Plus size={20} className="text-zinc-300" />
          <span className="text-[10px] font-medium text-zinc-400">More</span>
        </button>
      </div>
      {/* Expanded more options */}
      {showMore && (
        <div className="mt-3 flex gap-3 border-t border-white/5 pt-3">
          {MORE_TYPES.map(({ type, label, icon: Icon }) => (
            <button
              key={type}
              type="button"
              onClick={() => onSelect(type)}
              className={clsx(
                'flex flex-col items-center gap-1.5 rounded-lg px-3 py-2.5',
                'border border-white/10 transition-all duration-150',
                'hover:border-[#3ecf8e]/40 hover:bg-[#3ecf8e]/5',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
              )}
            >
              <Icon size={20} className="text-zinc-300" />
              <span className="text-[10px] font-medium text-zinc-400">{label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

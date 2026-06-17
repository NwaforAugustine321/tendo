import { Search, Bell, HelpCircle, Menu, ChevronDown, User } from 'lucide-react'

type Props = {
  onMenuClick: () => void
}

export function TopBar({ onMenuClick }: Props) {
  return (
    <header className="sticky top-0 z-20 flex min-h-[48px] shrink-0 items-center gap-2 border-b border-zinc-800/90 bg-[#0a0a0a]/95 px-3 backdrop-blur-md sm:gap-3 sm:px-4">
      {/* Mobile menu */}
      <button
        type="button"
        onClick={onMenuClick}
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-zinc-800 text-zinc-400 transition-colors hover:border-zinc-700 hover:bg-zinc-900 hover:text-white md:hidden"
        aria-label="Open menu"
      >
        <Menu size={18} />
      </button>

      {/* Left: Logo + breadcrumb */}
      <div className="hidden items-center gap-1.5 sm:flex">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
          <span className="flex items-center gap-[2px]">
            <span className="h-[4px] w-[4px] rounded-full bg-purple-600" />
            <span className="h-[4px] w-[4px] rounded-full bg-purple-600" />
          </span>
        </div>

        <span className="text-zinc-700">/</span>

        <button type="button" className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[13px] text-zinc-300 transition-colors hover:bg-zinc-800/50">
          <span className="font-medium">My Business</span>
          <span className="rounded border border-orange-500/35 bg-orange-950/40 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-orange-300">Free</span>
          <ChevronDown size={12} className="text-zinc-600" />
        </button>

        <span className="text-zinc-700">/</span>

        <button type="button" className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[13px] text-zinc-300 transition-colors hover:bg-zinc-800/50">
          <span className="font-medium">Tendo</span>
          <ChevronDown size={12} className="text-zinc-600" />
        </button>

        <span className="text-zinc-700">/</span>

        <button type="button" className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[13px] text-zinc-300 transition-colors hover:bg-zinc-800/50">
          <span className="font-medium">main</span>
          <span className="rounded border border-red-500/35 bg-red-950/40 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-red-300">Production</span>
          <ChevronDown size={12} className="text-zinc-600" />
        </button>
      </div>

      {/* Mobile brand */}
      <div className="flex items-center gap-1.5 sm:hidden">
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white border border-zinc-900">
          <span className="flex items-center gap-[1.5px]">
            <span className="h-[3px] w-[3px] rounded-full bg-purple-600" />
            <span className="h-[3px] w-[3px] rounded-full bg-purple-600" />
          </span>
        </div>
        <span className="text-[13px] font-semibold text-zinc-200">Tendo</span>
      </div>

      <div className="flex-1" />

      {/* Right */}
      <div className="flex items-center gap-1">
        <button type="button" className="hidden rounded px-2 py-1 text-[13px] text-zinc-500 transition-colors hover:text-zinc-300 sm:block">
          Feedback
        </button>

        <button
          type="button"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-900/40 px-2 text-[12px] text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300"
          aria-label="Search"
        >
          <Search size={14} />
          <span className="hidden sm:inline">Search...</span>
          <kbd className="hidden rounded border border-zinc-700/60 bg-zinc-800/50 px-1 py-0.5 text-[10px] font-medium text-zinc-500 sm:inline">⌘K</kbd>
        </button>

        <button
          type="button"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-800/50 hover:text-zinc-300"
          aria-label="Notifications"
        >
          <Bell size={16} />
        </button>

        <button
          type="button"
          className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-800/50 hover:text-zinc-300 sm:inline-flex"
          aria-label="Help"
        >
          <HelpCircle size={16} />
        </button>

        <button
          type="button"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-zinc-400 transition-colors hover:border-zinc-600 hover:bg-zinc-700 hover:text-zinc-200"
          aria-label="Account"
        >
          <User size={16} />
        </button>
      </div>
    </header>
  )
}

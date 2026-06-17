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
        aria-label="Open navigation menu"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      </button>

      {/* Left section: Logo + Org + Project + Branch */}
      <div className="hidden items-center gap-1.5 sm:flex">
        {/* Logo */}
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
          <span className="flex items-center gap-[2px]">
            <span className="h-[4px] w-[4px] rounded-full bg-purple-600" />
            <span className="h-[4px] w-[4px] rounded-full bg-purple-600" />
          </span>
        </div>

        {/* Separator */}
        <span className="text-zinc-700">/</span>

        {/* Org name + badge */}
        <button type="button" className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[13px] text-zinc-300 transition-colors hover:bg-zinc-800/50">
          <span className="font-medium">My Business</span>
          <span className="rounded border border-orange-500/35 bg-orange-950/40 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-orange-300">Free</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-zinc-600">
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* Separator */}
        <span className="text-zinc-700">/</span>

        {/* Project name + dropdown */}
        <button type="button" className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[13px] text-zinc-300 transition-colors hover:bg-zinc-800/50">
          <span className="font-medium">Tendo</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-zinc-600">
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* Separator */}
        <span className="text-zinc-700">/</span>

        {/* Branch / environment */}
        <button type="button" className="flex items-center gap-1.5 rounded px-1.5 py-1 text-[13px] text-zinc-300 transition-colors hover:bg-zinc-800/50">
          <span className="font-medium">main</span>
          <span className="rounded border border-red-500/35 bg-red-950/40 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-red-300">Production</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-zinc-600">
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
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

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right section */}
      <div className="flex items-center gap-1">
        {/* Feedback */}
        <button
          type="button"
          className="hidden rounded px-2 py-1 text-[13px] text-zinc-500 transition-colors hover:text-zinc-300 sm:block"
        >
          Feedback
        </button>

        {/* Search */}
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-900/40 px-2 text-[12px] text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300"
          aria-label="Search"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="1.5" />
            <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span className="hidden sm:inline">Search...</span>
          <kbd className="hidden rounded border border-zinc-700/60 bg-zinc-800/50 px-1 py-0.5 text-[10px] font-medium text-zinc-500 sm:inline">⌘K</kbd>
        </button>

        {/* Notifications */}
        <button
          type="button"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-800/50 hover:text-zinc-300"
          aria-label="Notifications"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Z" fill="currentColor" />
            <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* Help */}
        <button
          type="button"
          className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-800/50 hover:text-zinc-300 sm:inline-flex"
          aria-label="Help"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="12" cy="17" r="0.5" fill="currentColor" />
          </svg>
        </button>

        {/* Avatar */}
        <button
          type="button"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-zinc-400 transition-colors hover:border-zinc-600 hover:bg-zinc-700 hover:text-zinc-200"
          aria-label="Account"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 12a3.5 3.5 0 1 0-3.5-3.5A3.5 3.5 0 0 0 12 12Z" stroke="currentColor" strokeWidth="1.5" />
            <path d="M5.5 20.5c.8-3.2 3.5-5.5 6.5-5.5s5.7 2.3 6.5 5.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </header>
  )
}

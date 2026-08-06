export function InboxSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto">
      {[...Array(8)].map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-zinc-800/40 px-4 py-3 animate-pulse">
          <div className="h-4 w-4 rounded bg-zinc-800" />
          {/* <div className="h-4 w-4 rounded bg-zinc-800" /> */}
          {/* <div className="h-3 w-[120px] rounded bg-zinc-800" /> */}
          <div className="flex-1 flex gap-2">
            {/* <div className="h-3 w-[180px] rounded bg-zinc-800" /> */}
            <div className="h-3 w-[100px] rounded bg-zinc-800/60" />
          </div>
          <div className="h-3 w-[50px] rounded bg-zinc-800" />
        </div>
      ))}
    </div>
  )
}

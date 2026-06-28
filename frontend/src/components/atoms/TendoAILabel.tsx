import { useWorkspaceStore } from '../../store/workspace'

export function TendoAILabel() {
  const handleClick = () => {
    useWorkspaceStore.getState().toggleDashboardChat()
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="fixed bottom-4 right-4 z-50 flex items-center gap-2.5 rounded-xl bg-zinc-900/90 border border-zinc-800/60 px-4 py-2.5 cursor-pointer transition-all hover:border-zinc-700 hover:bg-zinc-800/90 shadow-lg"
    >
      <div className="flex flex-col items-start">
        <span className="text-xs font-semibold text-emerald-400">Tendo AI</span>
        <span className="text-[10px] text-zinc-400">Your business companion</span>
      </div>
      <span className="relative flex h-2 w-2 ml-1">
        <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>
    </button>
  )
}

import { Calendar, StickyNote, Mic } from "lucide-react";

/**
 * Right sidebar rail — thin vertical strip with icon buttons.
 * The mic icon starts voice communication with Tendo.
 */

const RAIL_ITEMS = [
  { id: "calendar", icon: <Calendar size={18} />, label: "Calendar" },
  { id: "notes", icon: <StickyNote size={18} />, label: "Notes" },
];

export function RightRail() {
  return (
    <aside
      className="hidden md:flex h-full w-[52px] flex-col items-center border-l border-zinc-800/60 bg-[#0f0f0f] py-3 gap-2"
      aria-label="Side panel"
    >
      {RAIL_ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
          aria-label={item.label}
          title={item.label}
        >
          {item.icon}
        </button>
      ))}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Mic button — starts voice communication */}
      <button
        type="button"
        className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
        aria-label="Start voice communication with Tendo"
        title="Start voice communication with Tendo"
      >
        <Mic size={20} />
      </button>
    </aside>
  );
}

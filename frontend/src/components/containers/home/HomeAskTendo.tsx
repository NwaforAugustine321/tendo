import { useState } from "react";
import { ArrowUp, Mic } from "lucide-react";
import { useWorkspaceStore } from "../../../store/workspace";

export function HomeAskTendo() {
  const [value, setValue] = useState("");

  const submit = (event?: any) => {
    event?.preventDefault();
    const message = value.trim();
    if (!message) return;
    useWorkspaceStore.getState().setPendingChatMessage(message);
    setValue("");
  };

  const toggleVoice = () => {
    window.dispatchEvent(new CustomEvent("tendo:voice-toggle"));
  };

  return (
    <form
      onSubmit={submit}
      className="rounded-2xl border border-zinc-800/70 bg-[#111111] p-3 shadow-sm"
    >
      <div className="flex items-end gap-3">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          rows={2}
          placeholder="Ask Tendo anything about your business..."
          className="min-h-[56px] flex-1 resize-none bg-transparent px-2 py-2 text-[14px] leading-relaxed text-zinc-200 outline-none placeholder:text-zinc-600"
        />
        <div className="flex items-center gap-2 pb-0.5">
          {/* <button
            type="button"
            onClick={toggleVoice}
            aria-label="Talk to Tendo"
            title="Talk to Tendo"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 transition-all hover:scale-[1.03] hover:bg-emerald-500/15 hover:text-emerald-300"
          >
            <Mic size={28} strokeWidth={2.2} />
          </button> */}
          <button
            type="submit"
            disabled={!value.trim()}
            aria-label="Send message"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-200 text-zinc-900 transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-20"
          >
            <ArrowUp size={17} strokeWidth={2.4} />
          </button>
        </div>
      </div>
      <div className="mt-2 px-2 text-[10px] text-zinc-600">
        Press Enter to ask · Shift + Enter for a new line
      </div>
    </form>
  );
}

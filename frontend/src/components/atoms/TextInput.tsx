import { useState, type KeyboardEvent } from "react";
import { ArrowUp, LoaderCircle, Mic, MicOff } from "lucide-react";

type Props = {
  onSend: (text: string) => void;
  placeholder?: string;
  onVoiceRecorded?: (blob: Blob) => void;
  onVoiceToggle?: () => void;
  isListening?: boolean;
  voiceLoading?: boolean;
};

export function TextInput({
  onSend,
  placeholder = "Ask Tendo anything about your business...",
  onVoiceToggle,
  isListening = false,
  voiceLoading = false,
}: Props) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    const trimmed = value.trim();

    if (!trimmed) return;

    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const micLabel = voiceLoading
    ? "Starting voice communication"
    : isListening
      ? "Stop voice communication"
      : "Start voice communication with Tendo";

  return (
    <div className="relative w-full">
      <div className="relative rounded-2xl border border-zinc-800/70 bg-[#111111] transition-colors focus-within:border-zinc-700">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={2}
          className="min-h-[56px] w-full resize-none bg-transparent px-4 py-3 pr-24 text-[13px] leading-relaxed text-zinc-200 outline-none placeholder:text-zinc-600"
        />

        <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1.5">
          {onVoiceToggle && (
            <button
              type="button"
              onClick={onVoiceToggle}
              disabled={voiceLoading}
              aria-label={micLabel}
              title={micLabel}
              className={`flex h-8 w-8 items-center justify-center rounded-full transition-all ${
                voiceLoading
                  ? "text-zinc-400"
                  : isListening
                    ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                    : "text-emerald-400 hover:bg-emerald-500/10"
              } disabled:cursor-not-allowed disabled:opacity-60`}
            >
              {voiceLoading ? (
                <LoaderCircle
                  size={16}
                  strokeWidth={2.2}
                  className="animate-spin"
                />
              ) : isListening ? (
                <MicOff size={16} strokeWidth={2.2} />
              ) : (
                <Mic size={16} strokeWidth={2.2} />
              )}
            </button>
          )}

          <button
            type="button"
            onClick={handleSend}
            disabled={!value.trim()}
            aria-label="Send message"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-200 text-zinc-900 transition-all hover:bg-white disabled:cursor-not-allowed disabled:opacity-20"
          >
            <ArrowUp size={16} strokeWidth={2.4} />
          </button>
        </div>
      </div>
    </div>
  );
}

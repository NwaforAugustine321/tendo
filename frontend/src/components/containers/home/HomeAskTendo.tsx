import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, LoaderCircle } from "lucide-react";
import { useAgentSessionStatus } from "../../../hooks/useAgentSessionStatus";
import { useVoiceAgentStore } from "../../../lib/voice-agent/store";
import { useWorkspaceStore } from "../../../store/workspace";

const BOTTOM_FOLLOW_THRESHOLD = 80;

type InteractionMode = "text" | "voice";

function getPresenceText(event: {
  event: string;
  data: Record<string, unknown>;
}): string {
  const data = event.data;

  if (data?.type !== "voice.presence" && data?.type !== "text.presence") {
    return "";
  }

  const payload = data.payload;

  if (!payload || typeof payload !== "object") {
    return "";
  }

  const message = (payload as Record<string, unknown>).message;

  return typeof message === "string" ? message.trim() : "";
}

export function HomeAskTendo() {
  const [value, setValue] = useState("");
  const [interactionMode, setInteractionMode] =
    useState<InteractionMode>("text");
  const [textRequestActive, setTextRequestActive] = useState(false);

  const wasTypingRef = useRef(false);
  const wasMicActiveRef = useRef(false);

  const { events: presenceEvents, clear: clearPresence } =
    useAgentSessionStatus(["voice.presence", "text.presence"]);

  const micActive = useVoiceAgentStore((state) => state.micActive);

  const agentSpeaking = useVoiceAgentStore((state) => state.agentSpeaking);

  const micLoading = useVoiceAgentStore((state: any) => state.micLoading);

  const stopMic = useVoiceAgentStore((state) => state.stopMic);

  let latestPresence = "";

  for (let index = presenceEvents.length - 1; index >= 0; index -= 1) {
    const text = getPresenceText(presenceEvents[index]);

    if (text) {
      latestPresence = text;
      break;
    }
  }

  useEffect(() => {
    if (wasTypingRef.current && !latestPresence) {
      setTextRequestActive(false);
    }

    wasTypingRef.current = Boolean(latestPresence);
  }, [latestPresence]);

  useEffect(() => {
    const wasMicActive = wasMicActiveRef.current;

    if (!wasMicActive && micActive) {
      setTextRequestActive(false);
      clearPresence();
      setInteractionMode("voice");
    }

    if (wasMicActive && !micActive) {
      setTextRequestActive(false);
      clearPresence();
      setInteractionMode("text");
    }

    wasMicActiveRef.current = micActive;
  }, [micActive, clearPresence]);

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();

    const message = value.trim();

    if (!message) return;

    clearPresence();

    setInteractionMode("text");
    setTextRequestActive(true);
    setValue("");

    useWorkspaceStore.getState().setPendingChatMessage(message);
  };

  const handleVoiceToggle = () => {
    clearPresence();
    setTextRequestActive(false);

    if (micActive) {
      stopMic();
      setInteractionMode("text");
    } else {
      setInteractionMode("voice");
    }

    window.dispatchEvent(new CustomEvent("tendo:voice-toggle"));
  };

  let displayedStatus = "";

  if (agentSpeaking) {
    displayedStatus = "Speaking...";
  } else if (latestPresence) {
    displayedStatus = latestPresence;
  } else if (micActive) {
    displayedStatus = "Listening...";
  } else if (textRequestActive) {
    displayedStatus = "Reasoning...";
  }

  return (
    <div className="w-full">
      {displayedStatus && (
        <div className="mb-2 flex justify-start">
          <div className="inline-flex w-fit items-center gap-2 rounded-2xl border border-zinc-800/90 bg-[#141414] px-4 py-2.5">
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
            </span>

            <span className="animate-pulse text-xs text-zinc-400">
              {displayedStatus}
            </span>
          </div>
        </div>
      )}

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
            <button
              type="button"
              onClick={handleVoiceToggle}
              disabled={micLoading}
              aria-label={micActive ? "Stop talking to Tendo" : "Talk to Tendo"}
              title={micActive ? "Stop talking to Tendo" : "Talk to Tendo"}
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-all ${
                micActive
                  ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                  : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
              } ${
                micLoading ? "cursor-not-allowed opacity-40" : "cursor-pointer"
              }`}
            >
              {micLoading ? (
                <LoaderCircle size={20} className="animate-spin" />
              ) : micActive ? (
                <MicOff size={20} />
              ) : (
                <Mic size={20} />
              )}
            </button>

            <button
              type="submit"
              disabled={!value.trim()}
              aria-label="Send message"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-200 text-zinc-900 transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-20"
            >
              <span className="text-[17px]">↑</span>
            </button>
          </div>
        </div>

        <div className="mt-2 px-2 text-[10px] text-zinc-600">
          Press Enter to ask · Shift + Enter for a new line
        </div>
      </form>
    </div>
  );
}

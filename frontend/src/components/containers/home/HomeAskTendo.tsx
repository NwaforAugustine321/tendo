import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, LoaderCircle } from "lucide-react";

import { useAgentSessionStatus } from "../../../hooks/useAgentSessionStatus";
import { useVoiceAgentStore } from "../../../lib/voice-agent/store";
import { useWorkspaceStore } from "../../../store/workspace";

type InteractionMode = "text" | "voice";

export function HomeAskTendo() {
  const [value, setValue] = useState("");
  const [interactionMode, setInteractionMode] =
    useState<InteractionMode>("text");
  const [initializing, setInitializing] = useState(false);

  const wasSpeakingRef = useRef(false);
  const wasMicActiveRef = useRef(false);

  const { presence, clear: clearPresence } = useAgentSessionStatus([
    "voice.presence",
    "text.presence",
  ]);

  const micActive = useVoiceAgentStore((state) => state.micActive);
  const agentSpeaking = useVoiceAgentStore((state) => state.agentSpeaking);
  const micLoading = useVoiceAgentStore((state: any) => state.micLoading);
  const stopMic = useVoiceAgentStore((state) => state.stopMic);

  const latestPresence = presence.text;

  /*
   * A new presence replaces the initial
   * Reasoning... state.
   */
  useEffect(() => {
    if (latestPresence) {
      setInitializing(false);
    }
  }, [latestPresence]);

  /*
   * When speaking finishes, the current
   * response is complete.
   *
   * Clear the response status. If voice is
   * still active, the status falls back to
   * Listening...
   */
  useEffect(() => {
    if (wasSpeakingRef.current && !agentSpeaking) {
      clearPresence();
      setInitializing(false);
    }

    wasSpeakingRef.current = agentSpeaking;
  }, [agentSpeaking, clearPresence]);

  /*
   * Voice lifecycle.
   *
   * Activating the microphone means the user
   * is ready to speak, so the status is
   * Listening..., not Reasoning....
   */
  useEffect(() => {
    const wasMicActive = wasMicActiveRef.current;

    if (!wasMicActive && micActive) {
      clearPresence();
      setInteractionMode("voice");
      setInitializing(false);
    }

    if (wasMicActive && !micActive) {
      clearPresence();
      setInteractionMode("text");
      setInitializing(false);
    }

    wasMicActiveRef.current = micActive;
  }, [micActive, clearPresence]);

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();

    const message = value.trim();

    if (!message) return;

    clearPresence();

    setInteractionMode("text");
    setInitializing(true);
    setValue("");

    useWorkspaceStore.getState().setPendingChatMessage(message);
  };

  const handleVoiceToggle = () => {
    clearPresence();

    if (micActive) {
      stopMic();
      setInteractionMode("text");
      setInitializing(false);
    } else {
      setInteractionMode("voice");
      setInitializing(false);
    }

    window.dispatchEvent(new CustomEvent("tendo:voice-toggle"));
  };

  /*
   * Status priority:
   *
   * 1. Speaking...
   * 2. Current presence
   * 3. Reasoning... for an active request
   * 4. Listening... while voice is active
   * 5. Nothing in text mode
   */
  let displayedStatus = "";

  if (agentSpeaking) {
    displayedStatus = "Speaking...";
  } else if (latestPresence) {
    displayedStatus = latestPresence;
  } else if (initializing) {
    displayedStatus = "Reasoning...";
  } else if (interactionMode === "voice" && micActive) {
    displayedStatus = "Listening...";
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

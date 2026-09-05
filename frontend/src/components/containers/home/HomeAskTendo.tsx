import { useEffect, useState } from "react";
import { Mic, MicOff, LoaderCircle } from "lucide-react";

import { useMessage } from "../../../hooks/useMessage";
import { useWorkspaceStore } from "../../../store/workspace";

export function HomeAskTendo() {
  const [value, setValue] = useState("");
  const [textActive, setTextActive] = useState(false);
  const [voiceActive, setVoiceActive] = useState(false);

  const {
    status,
    statusText,
    micActive,
    agentSpeaking,
    connectionState,
    response,
    transcript,
    stopMic,
  } = useMessage();

  const micLoading =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent" ||
    connectionState === "reconnecting" ||
    connectionState === "stopping";

  /*
   * Text lifecycle.
   *
   * The indicator starts when the user
   * submits text and stays visible until
   * the final response arrives.
   */
  useEffect(() => {
    if (status === "reasoning") {
      return;
    }

    if (response?.event === "message") {
      setTextActive(false);
    }
  }, [status, response]);

  /*
   * Voice lifecycle.
   *
   * Once a transcript arrives, the voice
   * request is being processed.
   *
   * Keep the indicator visible while Tendo
   * is reasoning or speaking.
   */
  useEffect(() => {
    if (transcript) {
      setVoiceActive(true);
    }

    if (response?.event === "voice.response" && !agentSpeaking) {
      setVoiceActive(false);
    }
  }, [transcript, response, agentSpeaking]);

  /*
   * The indicator is controlled by the
   * interaction lifecycle, NOT by whether
   * statusText happens to contain text.
   */
  const showIndicator = textActive || voiceActive || agentSpeaking;

  /*
   * statusText is only the content inside
   * the indicator.
   *
   * The indicator itself does not depend
   * on statusText.
   */
  const displayedStatus =
    statusText ||
    (agentSpeaking
      ? "Speaking..."
      : status === "reasoning"
        ? "Reasoning..."
        : voiceActive
          ? "Reasoning..."
          : "Reasoning...");

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();

    const message = value.trim();

    if (!message) {
      return;
    }

    setValue("");

    /*
     * Show the indicator immediately.
     * It does not matter whether the backend
     * has sent statusText yet.
     */
    setTextActive(true);

    useWorkspaceStore.getState().setPendingChatMessage(message);
  };

  const handleVoiceToggle = () => {
    if (micActive) {
      stopMic();
      setVoiceActive(false);
      return;
    }

    /*
     * Show the indicator immediately
     * when voice mode starts.
     */
    setVoiceActive(true);

    window.dispatchEvent(new CustomEvent("tendo:voice-toggle"));
  };

  return (
    <div className="w-full">
      {showIndicator && (
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

import { useEffect, useState } from "react";

import { Mic, MicOff, LoaderCircle } from "lucide-react";

import { useMessage } from "../../../hooks/useMessage";
import { useBusinessStore } from "../../../store/business";
import { useWorkspaceStore } from "../../../store/workspace";
import { EventType } from "../../../types/event";

export function HomeAskTendo() {
  const [value, setValue] = useState("");
  const [textActive, setTextActive] = useState(false);
  const [voiceActive, setVoiceActive] = useState(false);

  /*
   * Keep the active voice session ID so that stopping
   * voice can also stop the backend agent session.
   */
  const [voiceSessionId, setVoiceSessionId] = useState("");

  const { currentProfile } = useBusinessStore();
  const businessId = currentProfile?.id ?? "";

  const {
    isBusy,
    statusText,
    micActive,
    agentSpeaking,
    connectionState,
    response,
    transcript,
    stopMic,
    stopAgent,
    initAgent,
    startAgent,
  } = useMessage();

  const micLoading =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent" ||
    connectionState === "reconnecting" ||
    connectionState === "stopping";

  /*
   * TEXT REQUEST LIFECYCLE
   */
  useEffect(() => {
    if (response?.event !== EventType.Message) {
      return;
    }

    setTextActive(false);
  }, [response?.event]);

  /*
   * VOICE REQUEST LIFECYCLE
   *
   * The voice request becomes active once the
   * transcript arrives.
   */
  useEffect(() => {
    if (!transcript?.content) {
      return;
    }

    setVoiceActive(true);
  }, [transcript?.content]);

  /*
   * VOICE RESPONSE LIFECYCLE
   *
   * Keep the indicator active while Tendo is speaking.
   */
  useEffect(() => {
    if (response?.event !== EventType.VoiceResponse) {
      return;
    }

    if (!agentSpeaking) {
      setVoiceActive(false);
    }
  }, [response?.event, agentSpeaking]);

  /*
   * Make sure the local voice indicator is cleared
   * after Tendo finishes speaking.
   */
  useEffect(() => {
    if (agentSpeaking) {
      return;
    }

    if (!voiceActive) {
      return;
    }

    if (response?.event === EventType.VoiceResponse) {
      setVoiceActive(false);
    }
  }, [agentSpeaking, voiceActive, response?.event]);

  /*
   * TEXT SUBMISSION
   */
  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();

    const message = value.trim();

    if (!message) {
      return;
    }

    setVoiceActive(false);
    setValue("");
    setTextActive(true);

    useWorkspaceStore.getState().setPendingChatMessage(message);
  };

  const handleVoiceToggle = async () => {
    if (micLoading) {
      return;
    }

    /*
     * STOP VOICE
     *
     * Previously this only stopped the microphone.
     * Now it also stops the backend voice agent/session.
     */
    if (micActive) {
      stopMic();

      setVoiceActive(false);

      /*
       * stopAgent requires both IDs.
       *
       * If for some reason the local session ID is
       * unavailable, the microphone has still already
       * been stopped, so don't block the UI cleanup.
       */
      if (businessId && voiceSessionId) {
        try {
          await stopAgent(businessId, voiceSessionId);
        } catch {
          /*
           * stopAgent already handles the user-facing
           * error/toast. Do not expose internal errors here.
           */
        }
      }

      setVoiceSessionId("");

      return;
    }

    if (!businessId) {
      return;
    }

    try {
      setVoiceActive(true);

      const session = await initAgent(businessId);

      /*
       * Save the session ID before starting the agent.
       * This is then used when the user clicks stop.
       */
      setVoiceSessionId(session.session_id);

      await startAgent(businessId, session.session_id);
    } catch {
      setVoiceActive(false);
      setVoiceSessionId("");
    }
  };

  return (
    <div className="w-full">
      {isBusy && (
        <div className="mb-2 flex justify-start">
          <div className="inline-flex w-fit items-center gap-2 rounded-2xl border border-zinc-800/90 bg-[#141414] px-4 py-2.5">
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
            </span>

            <span className="animate-pulse text-xs text-zinc-400">
              {statusText}
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
              onClick={() => {
                void handleVoiceToggle();
              }}
              disabled={micLoading || !businessId}
              aria-label={micActive ? "Stop talking to Tendo" : "Talk to Tendo"}
              title={micActive ? "Stop talking to Tendo" : "Talk to Tendo"}
              className={[
                "flex h-9 w-9 shrink-0 items-center",
                "justify-center rounded-full border",
                "transition-all",
                micActive
                  ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                  : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300",
                micLoading || !businessId
                  ? "cursor-not-allowed opacity-40"
                  : "cursor-pointer",
              ].join(" ")}
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

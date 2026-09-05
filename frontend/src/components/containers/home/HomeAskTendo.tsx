import { useEffect, useState } from "react";

import { Mic, MicOff, LoaderCircle } from "lucide-react";

import { useMessage } from "../../../hooks/useMessage";

import { useWorkspaceStore } from "../../../store/workspace";

import { EventType } from "../../../types/event";

export function HomeAskTendo() {
  const [value, setValue] = useState("");

  const [textActive, setTextActive] = useState(false);

  const [voiceActive, setVoiceActive] = useState(false);

  const {
    status,
    isBusy,
    statusText,
    micActive,
    agentSpeaking,
    connectionState,
    response,
    transcript,
    presence,
    stopMic,
  } = useMessage();

  const micLoading =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent" ||
    connectionState === "reconnecting" ||
    connectionState === "stopping";

  /*
   * TEXT REQUEST LIFECYCLE
   *
   * A text request is started locally by submit().
   *
   * We keep textActive=true until the FINAL text
   * response arrives.
   *
   * Do not use `status === idle` here because the
   * status/reasoning state belongs to this particular
   * useMessage() instance.
   */
  useEffect(() => {
    if (response?.event !== EventType.Message) {
      return;
    }

    /*
     * Final text response received.
     *
     * This is the reset point for the text indicator.
     */
    setTextActive(false);
  }, [response?.event]);

  /*
   * VOICE REQUEST LIFECYCLE
   *
   * A voice request becomes active when the transcript
   * arrives.
   *
   * Keep the indicator visible until voice.response
   * has completed speaking.
   */
  useEffect(() => {
    if (transcript?.content) {
      setVoiceActive(true);
    }
  }, [transcript?.content]);

  useEffect(() => {
    if (response?.event !== EventType.VoiceResponse) {
      return;
    }

    /*
     * The voice response has arrived.
     *
     * Keep the indicator while Tendo is speaking.
     * It is cleared once speaking has finished.
     */
    if (!agentSpeaking) {
      setVoiceActive(false);
    }
  }, [response?.event, agentSpeaking]);

  /*
   * When the agent finishes speaking, make sure the
   * voice indicator is reset.
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
   * IMPORTANT
   *
   * Do NOT gate this with:
   *
   *   status !== "idle"
   *
   * because HomeAskTendo's local useMessage()
   * can still have status="idle" while another
   * useMessage() instance is processing the request.
   *
   * textActive / voiceActive are the local indicator
   * lifecycle for this component.
   */
  //   const showIndicator = isBusy; // textActive || voiceActive || agentSpeaking;

  /*
   * STATUS DISPLAY
   *
   * statusText remains LIVE.
   *
   * We intentionally do NOT store statusText in local
   * state. Every new statusText value from useMessage()
   * should immediately be reflected here.
   *
   * Priority:
   *
   * 1. Speaking... while the agent is speaking
   * 2. statusText when available
   * 3. Reasoning... while text/voice processing
   */
  //   const displayedStatus = agentSpeaking ? "Speaking..." : statusText;

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();

    const message = value.trim();

    if (!message) {
      return;
    }

    /*
     * Reset any previous voice indicator before
     * starting a new text request.
     */
    setVoiceActive(false);

    /*
     * Clear the input immediately.
     */
    setValue("");

    /*
     * Start the local text indicator immediately.
     *
     * This is important because the HomeAskTendo
     * useMessage() instance is separate from the
     * Conversation useMessage() instance.
     */
    setTextActive(true);

    /*
     * The workspace/Conversation flow owns the
     * actual request execution.
     */
    useWorkspaceStore.getState().setPendingChatMessage(message);
  };

  const handleVoiceToggle = () => {
    if (micActive) {
      stopMic();

      /*
       * Stopping the microphone ends the local
       * voice indicator if there is no response
       * currently being spoken.
       */
      if (!agentSpeaking) {
        setVoiceActive(false);
      }

      return;
    }

    /*
     * Starting the microphone itself does not mean
     * a request is being processed.
     *
     * The actual voice request begins when the
     * transcript arrives.
     */
    setVoiceActive(true);

    window.dispatchEvent(new CustomEvent("tendo:voice-toggle"));
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

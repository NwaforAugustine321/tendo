import { Calendar, StickyNote, Mic, MicOff, LoaderCircle } from "lucide-react";

import { useState } from "react";

import { useMessage } from "../../hooks/useMessage";
import { useBusinessStore } from "../../store/business";
import { SpeakingIndicator } from "../atoms/SpeakingIndicator";

const RAIL_ITEMS = [
  {
    id: "calendar",
    icon: <Calendar size={18} />,
    label: "Calendar",
  },
  {
    id: "notes",
    icon: <StickyNote size={18} />,
    label: "Notes",
  },
];

export function RightRail() {
  const [voiceSessionId, setVoiceSessionId] = useState("");

  const { currentProfile } = useBusinessStore();
  const businessId = currentProfile?.id ?? "";

  const {
    connectionState,
    micActive,
    agentSpeaking,
    isVoiceMode,
    initAgent,
    startAgent,
    stopMic,
    stopAgent,
    statusText,
  } = useMessage();

  const isActive = isVoiceMode || micActive || agentSpeaking;

  const micLoading =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent" ||
    connectionState === "reconnecting" ||
    connectionState === "stopping";

  const handleMicClick = async () => {
    if (micLoading || !businessId) {
      return;
    }

    /*
     * STOP VOICE
     *
     * Stop both the local microphone and the
     * backend voice agent/session.
     */
    if (micActive) {
      stopMic();

      if (voiceSessionId) {
        try {
          await stopAgent(businessId, voiceSessionId);
        } catch {
          /*
           * stopAgent handles the user-facing
           * error state/toast.
           *
           * Do not expose internal errors here.
           */
        }
      }

      setVoiceSessionId("");

      return;
    }

    try {
      /*
       * Initialize the voice session using the
       * business ID from the workspace store.
       */
      const session = await initAgent(businessId);

      /*
       * Keep the session ID so the same voice
       * session can be explicitly stopped later.
       */
      setVoiceSessionId(session.session_id);

      /*
       * Start the agent using the session ID
       * returned by initAgent.
       */
      await startAgent(businessId, session.session_id);
    } catch {
      setVoiceSessionId("");

      return;
    }
  };

  const displayStatus = statusText;

  const micLabel = micLoading
    ? displayStatus || "Starting voice communication"
    : micActive
      ? "Stop voice communication"
      : "Start voice communication with Tendo";

  return (
    <>
      <SpeakingIndicator active={isActive} />

      <aside
        className={[
          "hidden h-full w-[52px] flex-col items-center gap-2",
          "border-l border-zinc-800/60 bg-[#0f0f0f] py-3 md:flex",
        ].join(" ")}
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

        <div className="flex-1" />

        <button
          type="button"
          onClick={() => {
            void handleMicClick();
          }}
          disabled={micLoading || !businessId}
          className={[
            "flex h-9 w-9 items-center justify-center rounded-full",
            "transition-colors",
            micActive
              ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
              : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300",
            micLoading || !businessId
              ? "cursor-not-allowed opacity-40"
              : "cursor-pointer",
          ].join(" ")}
          aria-label={micLabel}
          title={micLabel}
        >
          {micLoading ? (
            <LoaderCircle size={20} className="animate-spin" />
          ) : micActive ? (
            <MicOff size={20} />
          ) : (
            <Mic size={20} />
          )}
        </button>
      </aside>
    </>
  );
}

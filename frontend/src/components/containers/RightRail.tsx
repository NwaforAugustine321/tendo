import { Calendar, StickyNote, Mic, MicOff, LoaderCircle } from "lucide-react";

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

    if (micActive) {
      stopMic();
      return;
    }

    try {
      /*
       * Initialize the voice session using the
       * business ID from the workspace store.
       *
       * initAgent returns the VoiceSession.
       */
      const session = await initAgent(businessId);

      /*
       * Start the agent using the same business ID
       * and the session ID returned by initAgent.
       */
      await startAgent(businessId, session.session_id);
    } catch {
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

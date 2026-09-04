import { Calendar, StickyNote, Mic, MicOff } from "lucide-react";

import { useVoiceAgentStore } from "../../lib/voice-agent/store";

import { SpeakingIndicator } from "../SpeakingIndicator";

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
  const {
    connectionState,
    businessId,
    micActive,
    agentSpeaking,
    statusText,
    initAgent,
    startAgent,
    stopMic,
  } = useVoiceAgentStore();

  const isActive = micActive || agentSpeaking;

  const canUseMic =
    connectionState === "ready" ||
    connectionState === "listening" ||
    connectionState === "speaking";

  const canRetry =
    connectionState === "error" || connectionState === "disconnected";

  const micDisabled =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent" ||
    connectionState === "reconnecting";

  const handleMicClick = async () => {
    if (micActive) {
      stopMic();
      return;
    }

    if (canUseMic) {
      await startAgent();
      return;
    }

    if (canRetry && businessId) {
      try {
        await initAgent(businessId);

        const state = useVoiceAgentStore.getState();

        if (state.connectionState === "ready" && state.agentReady) {
          await startAgent();
        }
      } catch {
        return;
      }
    }
  };

  let displayStatus = "";

  if (connectionState === "initializing") {
    displayStatus = "Initializing voice...";
  } else if (connectionState === "connecting") {
    displayStatus = "Connecting...";
  } else if (connectionState === "waiting_for_agent") {
    displayStatus = "Starting agent...";
  } else if (agentSpeaking) {
    displayStatus = "Tendo is speaking...";
  } else if (connectionState === "error") {
    displayStatus = statusText || "Voice connection failed";
  } else if (connectionState === "reconnecting") {
    displayStatus = "Reconnecting...";
  } else if (micActive) {
    displayStatus = "Listening...";
  } else if (statusText) {
    displayStatus = statusText;
  }

  const micLabel = micActive
    ? "Stop voice communication"
    : canRetry
      ? "Retry voice connection"
      : "Start voice communication with Tendo";

  return (
    <>
      <SpeakingIndicator
        active={isActive}
        speaking={agentSpeaking}
        statusText={displayStatus}
      />

      <aside
        className="hidden h-full w-[52px] flex-col items-center gap-2 border-l border-zinc-800/60 bg-[#0f0f0f] py-3 md:flex"
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
          disabled={micDisabled || !businessId}
          className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
            micActive
              ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
              : canRetry
                ? "text-zinc-300 hover:bg-white/10 hover:text-white"
                : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
          } ${
            micDisabled || !businessId
              ? "cursor-not-allowed opacity-40"
              : "cursor-pointer"
          }`}
          aria-label={micLabel}
          title={micLabel}
        >
          {micActive ? <MicOff size={20} /> : <Mic size={20} />}
        </button>
      </aside>
    </>
  );
}

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
    micActive,
    agentSpeaking,
    statusText,
    startAgent,
    stopMic,
  } = useVoiceAgentStore();

  const isActive = micActive || agentSpeaking;

  const handleMicClick = async () => {
    if (micActive) {
      stopMic();
      return;
    }

    await startAgent();
  };

  let displayStatus = "";

  if (agentSpeaking) {
    displayStatus = "Tendo is speaking...";
  } else if (statusText) {
    displayStatus = statusText;
  } else if (micActive) {
    displayStatus = "Listening...";
  }

  const micDisabled =
    connectionState === "disconnected" ||
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent" ||
    connectionState === "error";

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
          onClick={handleMicClick}
          disabled={micDisabled}
          className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
            micActive
              ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
              : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
          } ${micDisabled ? "cursor-not-allowed opacity-40" : ""}`}
          aria-label={
            micActive
              ? "Stop voice communication"
              : "Start voice communication with Tendo"
          }
          title={
            micActive
              ? "Stop voice communication"
              : "Start voice communication with Tendo"
          }
        >
          {micActive ? <MicOff size={20} /> : <Mic size={20} />}
        </button>
      </aside>
    </>
  );
}

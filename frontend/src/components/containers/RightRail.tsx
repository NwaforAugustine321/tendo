import { Calendar, StickyNote, Mic, MicOff } from "lucide-react";
import { useVoiceStore } from "../../store/voice";
import { SpeakingIndicator } from "../SpeakingIndicator";

/**
 * Right sidebar rail — thin vertical strip with icon buttons.
 * The mic icon starts voice communication with Tendo.
 */

const RAIL_ITEMS = [
  { id: "calendar", icon: <Calendar size={18} />, label: "Calendar" },
  { id: "notes", icon: <StickyNote size={18} />, label: "Notes" },
];

export function RightRail() {
  const { connectionState, micActive, agentSpeaking, statusText, toggleMic } =
    useVoiceStore();

  const isActive = micActive || agentSpeaking;

  const handleMicClick = async () => {
    await toggleMic();
  };

  // When speaking: show speaking text. When listening: show listening.
  // Only show progress statusText during processing (not speaking/listening).
  let displayStatus = "";
  if (agentSpeaking) {
    displayStatus = "Tendo is speaking...";
  } else if (statusText) {
    displayStatus = statusText;
  } else if (micActive) {
    displayStatus = "Listening...";
  }

  return (
    <>
      {/* Speaking indicator — top right when voice is active */}
      <SpeakingIndicator
        active={isActive}
        speaking={agentSpeaking}
        statusText={displayStatus}
      />

      <aside
        className="hidden md:flex h-full w-[52px] flex-col items-center border-l border-zinc-800/60 bg-[#0f0f0f] py-3 gap-2"
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

        {/* Spacer */}
        <div className="flex-1" />

        {/* Mic button — toggles voice communication */}
        <button
          type="button"
          onClick={handleMicClick}
          className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
            micActive
              ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
              : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
          }`}
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

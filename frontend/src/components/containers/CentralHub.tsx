import { useState, useEffect } from "react";
import { Mic, AudioLines } from "lucide-react";
import clsx from "clsx";

type Props = {
  onMicClick?: () => void;
  compact?: boolean;
};

export function CentralHub({ onMicClick, compact = false }: Props) {
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    const handleRecordingState = (e: Event) => {
      setIsRecording((e as CustomEvent).detail?.recording ?? false);
    };
    window.addEventListener("tendo:recording-state", handleRecordingState);
    return () =>
      window.removeEventListener("tendo:recording-state", handleRecordingState);
  }, []);

  return (
    <button
      type="button"
      onClick={onMicClick}
      className={clsx(
        "relative flex flex-col items-center justify-center rounded-full focus:outline-none",
        compact ? "w-12 h-12" : "aspect-square w-[clamp(160px,18vw,240px)]",
      )}
    >
      {/* Glow ring */}
      <div
        className={clsx(
          "absolute inset-0 rounded-full border transition-all duration-300",
          isRecording
            ? "border-red-400/40 shadow-[0_0_20px_rgba(248,113,113,0.2)]"
            : "border-emerald-500/30 shadow-[0_0_20px_rgba(16,185,129,0.15)]",
        )}
      />

      {!compact && (
        <>
          {/* Second ring */}
          <div
            className={clsx(
              "absolute inset-[8%] rounded-full border transition-colors duration-300",
              isRecording ? "border-red-500/20" : "border-emerald-600/20",
            )}
          />
          {/* Third dark ring */}
          <div className="absolute inset-[18%] rounded-full border border-zinc-700/30 bg-[#0d0d0d]" />
          {/* Inner dark filled circle */}
          <div className="absolute inset-[28%] rounded-full bg-[#0a0a0a] border border-zinc-800/40" />
        </>
      )}

      {compact && (
        <div className="absolute inset-[4px] rounded-full bg-[#0d0d0d] border border-zinc-800/40" />
      )}

      {/* Ping animation when recording */}
      {isRecording && (
        <span className="absolute inset-0 animate-ping rounded-full border border-red-400/20" />
      )}

      {/* Center content */}
      <div className="relative z-10 flex flex-col items-center gap-0.5">
        <Mic
          size={compact ? 16 : 20}
          className={clsx(
            "transition-colors duration-300",
            isRecording ? "text-red-400" : "text-emerald-400",
          )}
        />
        {!compact && (
          <>
            <span className="text-sm font-medium text-white mt-1">
              {isRecording ? "Listening..." : "Ask Tendo"}
            </span>
            <span
              className={clsx(
                "text-[10px] text-center leading-tight transition-colors duration-300",
                isRecording ? "text-red-400/70" : "text-zinc-500",
              )}
            >
              {isRecording ? (
                "Tap to stop"
              ) : (
                <>
                  Ask anything about your
                  <br />
                  business
                </>
              )}
            </span>
            <AudioLines
              size={14}
              className={clsx(
                "mt-0.5 transition-colors duration-300",
                isRecording ? "text-red-500/50" : "text-emerald-600/50",
              )}
            />
          </>
        )}
      </div>
    </button>
  );
}

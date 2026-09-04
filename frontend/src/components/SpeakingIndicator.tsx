import { useEffect, useRef, useState } from "react";

import { useAgentSessionStatus } from "../hooks/useAgentSessionStatus";
import { useVoiceAgentStore } from "../lib/voice-agent/store";

type Props = {
  active: boolean;
};

export function SpeakingIndicator({ active }: Props) {
  const { agentSpeaking } = useVoiceAgentStore();

  const { presence, clear } = useAgentSessionStatus([
    "voice.presence",
    "text.presence",
    "message",
  ]);

  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [pulse, setPulse] = useState(0);

  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wasSpeaking = useRef(false);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!active) {
      setPulse(0);
      clear();
      wasSpeaking.current = false;
      return;
    }

    intervalRef.current = setInterval(() => {
      setPulse(Math.random());
    }, 120);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active, clear]);

  /*
   * When speaking finishes, remove the previous response/presence
   * so the indicator returns to Listening...
   */
  useEffect(() => {
    if (wasSpeaking.current && !agentSpeaking) {
      clear();
    }

    wasSpeaking.current = agentSpeaking;
  }, [agentSpeaking, clear]);

  const handlePointerDown = (e: React.PointerEvent) => {
    dragging.current = true;

    offset.current = {
      x: e.clientX - pos.x,
      y: e.clientY - pos.y,
    };

    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragging.current) return;

    setPos({
      x: e.clientX - offset.current.x,
      y: e.clientY - offset.current.y,
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    dragging.current = false;

    if ((e.currentTarget as HTMLElement).hasPointerCapture(e.pointerId)) {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    }
  };

  if (!active) return null;

  const presenceText = presence.text.trim();

  /*
   * Strict display priority:
   *
   * 1. Speaking
   * 2. Presence/status text
   * 3. Listening
   */
  let displayText = "Listening...";

  if (agentSpeaking) {
    displayText = "Speaking...";
  } else if (presenceText) {
    displayText = presenceText;
  }

  const orbScale = 1 + pulse * 0.045;
  const glowScale = 1 + pulse * 0.16;

  const glowOpacity = 0.16 + pulse * 0.14;
  const whiteOpacity = 0.78 + pulse * 0.18;

  return (
    <div
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className="fixed left-10 top-20 z-50 h-[125px] w-[180px] cursor-grab select-none touch-none active:cursor-grabbing"
      style={{
        transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
      }}
    >
      <div className="absolute left-1/2 top-[42px] h-[82px] w-[82px] -translate-x-1/2 -translate-y-1/2">
        <div
          className="pointer-events-none absolute -inset-10 rounded-full"
          style={{
            background: `radial-gradient(
              circle,
              rgba(0,131,255,${glowOpacity}) 0%,
              rgba(79,194,255,${0.1 + pulse * 0.08}) 32%,
              rgba(188,238,255,${0.06 + pulse * 0.05}) 48%,
              rgba(255,255,255,0) 74%
            )`,
            filter: "blur(13px)",
            transform: `scale(${glowScale})`,
            transition: "transform 120ms ease-out",
          }}
        />

        <div
          className="pointer-events-none absolute left-1/2 top-1/2 h-[96px] w-[96px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-sky-300/20"
          style={{
            transform: `translate(-50%, -50%) scale(${1.04 + pulse * 0.18})`,
            opacity: 0.16 + pulse * 0.1,
            transition: "transform 120ms ease-out, opacity 120ms ease-out",
          }}
        />

        <div
          className="pointer-events-none absolute left-1/2 top-1/2 h-[108px] w-[108px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-sky-400/10"
          style={{
            transform: `translate(-50%, -50%) scale(${1.06 + pulse * 0.25})`,
            opacity: 0.1 + pulse * 0.08,
            transition: "transform 120ms ease-out, opacity 120ms ease-out",
          }}
        />

        <div
          className="absolute inset-0"
          style={{
            transform: `scale(${orbScale})`,
            transition: "transform 120ms ease-out",
          }}
        >
          <div
            className="relative h-full w-full overflow-hidden rounded-full"
            style={{
              background: `radial-gradient(
                circle at 62% 25%,
                rgba(255,255,255,${0.94 + pulse * 0.06}) 0%,
                rgba(241,252,255,${0.88 + pulse * 0.08}) 20%,
                rgba(207,243,255,${0.84 + pulse * 0.08}) 40%,
                rgba(91,199,255,${0.86 + pulse * 0.08}) 63%,
                rgba(0,131,255,${0.94 + pulse * 0.06}) 100%
              )`,
              boxShadow: `
                0 0 ${20 + pulse * 14}px rgba(0,131,255,${0.24 + pulse * 0.18}),
                0 0 ${42 + pulse * 24}px rgba(0,131,255,${0.1 + pulse * 0.12}),
                inset 0 0 ${18 + pulse * 10}px rgba(255,255,255,${
                  0.16 + pulse * 0.14
                })
              `,
              filter: `brightness(${1 + pulse * 0.1})`,
              transition:
                "background 120ms ease-out, box-shadow 120ms ease-out, filter 120ms ease-out",
            }}
          >
            <div
              className="absolute inset-[-20%]"
              style={{
                background: `radial-gradient(
                  ellipse at 56% 38%,
                  rgba(255,255,255,${whiteOpacity}) 0%,
                  rgba(255,255,255,${0.7 + pulse * 0.18}) 22%,
                  rgba(255,255,255,${0.2 + pulse * 0.12}) 46%,
                  rgba(255,255,255,0) 70%
                )`,
                transform: `translate3d(
                  ${pulse * 5 - 2.5}px,
                  ${pulse * -4}px,
                  0
                ) scale(${1 + pulse * 0.08})`,
                transition: "transform 120ms ease-out",
              }}
            />

            <div
              className="absolute inset-[-15%]"
              style={{
                background: `radial-gradient(
                  ellipse at 68% 20%,
                  rgba(255,255,255,${0.34 + pulse * 0.26}) 0%,
                  rgba(231,249,255,${0.2 + pulse * 0.14}) 32%,
                  rgba(255,255,255,0) 68%
                )`,
                transform: `translate3d(
                  ${pulse * -3}px,
                  ${pulse * -3}px,
                  0
                ) scale(${1 + pulse * 0.06})`,
                transition: "transform 120ms ease-out",
              }}
            />

            <div
              className="absolute inset-[-18%]"
              style={{
                background: `radial-gradient(
                  ellipse at 32% 86%,
                  rgba(0,131,255,${0.72 + pulse * 0.18}) 0%,
                  rgba(0,131,255,${0.42 + pulse * 0.18}) 28%,
                  rgba(0,131,255,${0.12 + pulse * 0.08}) 54%,
                  rgba(0,131,255,0) 72%
                )`,
                transform: `translate3d(
                  ${pulse * -3}px,
                  ${pulse * 3}px,
                  0
                ) scale(${1 + pulse * 0.05})`,
                transition: "transform 120ms ease-out",
              }}
            />

            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background: `linear-gradient(
                  135deg,
                  rgba(255,255,255,${0.24 + pulse * 0.2}) 0%,
                  rgba(255,255,255,${0.08 + pulse * 0.1}) 28%,
                  rgba(255,255,255,0) 48%,
                  rgba(0,131,255,${0.12 + pulse * 0.08}) 100%
                )`,
              }}
            />

            <div
              className="pointer-events-none absolute left-[18%] top-[13%] h-[28%] w-[38%] rounded-full"
              style={{
                background: `radial-gradient(
                  ellipse,
                  rgba(255,255,255,${0.72 + pulse * 0.2}) 0%,
                  rgba(255,255,255,${0.18 + pulse * 0.12}) 42%,
                  rgba(255,255,255,0) 72%
                )`,
                filter: "blur(5px)",
                transform: `translate3d(
                  ${pulse * 2}px,
                  ${pulse * -1}px,
                  0
                ) scale(${1 + pulse * 0.08})`,
                transition: "transform 120ms ease-out",
              }}
            />
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute left-1/2 top-[91px] w-[100px] -translate-x-1/2">
        <div className="mx-auto w-full rounded-2xl border border-white/[0.08] bg-zinc-950/75 px-3 py-1.5 text-center text-[10px] font-medium text-zinc-300 shadow-lg backdrop-blur-md">
          <span className="block max-h-[48px] overflow-hidden break-words leading-[14px]">
            {displayText}
          </span>
        </div>
      </div>
    </div>
  );
}

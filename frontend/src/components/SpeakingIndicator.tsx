import { useEffect, useRef, useState } from "react";

type Props = {
  active: boolean;
  speaking: boolean;
  statusText?: string;
};

function useStreamText(text: string) {
  const [displayed, setDisplayed] = useState("");
  const throttleRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intervalRef2 = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!text) {
      setDisplayed("");
      if (throttleRef.current) {
        clearTimeout(throttleRef.current);
        throttleRef.current = null;
      }
      if (intervalRef2.current) {
        clearInterval(intervalRef2.current);
        intervalRef2.current = null;
      }
      return;
    }

    // Throttle: ignore rapid changes within 800ms
    if (throttleRef.current) return;

    // Stream the accepted text character by character
    if (intervalRef2.current) clearInterval(intervalRef2.current);
    setDisplayed("");
    let i = 0;
    intervalRef2.current = setInterval(() => {
      i += 2;
      if (i >= text.length) {
        setDisplayed(text);
        if (intervalRef2.current) clearInterval(intervalRef2.current);
      } else {
        setDisplayed(text.slice(0, i));
      }
    }, 18);

    throttleRef.current = setTimeout(() => {
      throttleRef.current = null;
    }, 800);

    return () => {
      if (intervalRef2.current) clearInterval(intervalRef2.current);
    };
  }, [text]);

  return displayed;
}

const NUM_BARS = 16;
const IDLE_BARS = Array.from({ length: NUM_BARS }, () => 0.25);

export function SpeakingIndicator({ active, speaking, statusText }: Props) {
  const [bars, setBars] = useState(IDLE_BARS);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });
  const elRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamedText = useStreamText(statusText || "");

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (speaking) {
      intervalRef.current = setInterval(() => {
        setBars((prev) => prev.map(() => 0.25 + Math.random() * 0.75));
      }, 120);
    } else if (active) {
      intervalRef.current = setInterval(() => {
        setBars((prev) => prev.map(() => 0.2 + Math.random() * 0.2));
      }, 300);
    } else {
      setBars(IDLE_BARS);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [speaking, active]);

  const handlePointerDown = (e: React.PointerEvent) => {
    dragging.current = true;
    offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragging.current) return;
    setPos({
      x: e.clientX - offset.current.x,
      y: e.clientY - offset.current.y,
    });
  };

  const handlePointerUp = () => {
    dragging.current = false;
  };

  if (!active) return null;

  const halfBars = Math.floor(NUM_BARS / 2);

  return (
    <div
      ref={elRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className="fixed top-4 right-14 z-50 flex flex-col items-center gap-1.5 cursor-grab active:cursor-grabbing select-none touch-none"
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      <div className="flex items-center gap-3 rounded-full bg-zinc-900/90 px-5 py-2 shadow-lg backdrop-blur-sm border border-zinc-700/50 min-w-[200px] justify-center">
        <div className="flex items-center justify-center gap-[3px] h-5 flex-1">
          {bars.slice(0, halfBars).map((height, i) => (
            <div
              key={`l-${i}`}
              className="w-[3px] rounded-full bg-emerald-400"
              style={{
                height: `${height * 100}%`,
                transition: "height 120ms ease-out",
              }}
            />
          ))}
        </div>

        <div className="w-8 h-8 rounded-full bg-white border border-zinc-700 flex items-center justify-center shrink-0">
          <span className="flex items-center gap-[3px]">
            <span
              className={`h-[4px] w-[4px] rounded-full bg-purple-600 ${speaking ? "animate-pulse" : ""}`}
            />
            <span
              className={`h-[4px] w-[4px] rounded-full bg-purple-600 ${speaking ? "animate-pulse" : ""}`}
            />
          </span>
        </div>

        <div className="flex items-center justify-center gap-[3px] h-5 flex-1">
          {bars.slice(halfBars).map((height, i) => (
            <div
              key={`r-${i}`}
              className="w-[3px] rounded-full bg-emerald-400"
              style={{
                height: `${height * 100}%`,
                transition: "height 120ms ease-out",
              }}
            />
          ))}
        </div>
      </div>

      {streamedText && (
        <span className="text-[10px] text-zinc-300 max-w-[300px] text-center truncate bg-zinc-900/90 px-3 py-0.5 rounded-full backdrop-blur-sm border border-zinc-700/50 whitespace-nowrap">
          {streamedText}
        </span>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";

type Props = {
  active: boolean;
  speaking: boolean;
  statusText?: string;
};

function useStreamText(text: string, speed = 20) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    if (!text) {
      setDisplayed("");
      return;
    }
    let i = 0;
    setDisplayed("");
    const interval = setInterval(() => {
      i += 2;
      if (i >= text.length) {
        setDisplayed(text);
        clearInterval(interval);
      } else {
        setDisplayed(text.slice(0, i));
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);
  return displayed;
}

export function SpeakingIndicator({ active, speaking, statusText }: Props) {
  const [bars, setBars] = useState([0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });
  const elRef = useRef<HTMLDivElement>(null);
  const streamedStatus = useStreamText(statusText || "");

  useEffect(() => {
    if (!speaking) {
      setBars([0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]);
      return;
    }
    const interval = setInterval(() => {
      setBars((prev) => prev.map(() => 0.3 + Math.random() * 0.7));
    }, 100);
    return () => clearInterval(interval);
  }, [speaking]);

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

  return (
    <div
      ref={elRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className="fixed top-4 right-4 z-50 flex flex-col items-center gap-1 cursor-grab active:cursor-grabbing select-none touch-none"
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      <div className="flex items-center gap-2 rounded-full bg-zinc-900/90 px-3 py-2 shadow-lg backdrop-blur-sm border border-zinc-700/50">
        <div className="flex items-center gap-[2px] h-5">
          {bars.slice(0, 3).map((height, i) => (
            <div
              key={`l-${i}`}
              className="w-[3px] rounded-full bg-emerald-400"
              style={{
                height: speaking ? `${height * 100}%` : "30%",
                transition: speaking ? "height 80ms" : "height 300ms",
              }}
            />
          ))}
        </div>

        <div className="w-8 h-8 rounded-full bg-white border border-zinc-700 flex items-center justify-center">
          <span className="flex items-center gap-[2px]">
            <span
              className={`h-[4px] w-[4px] rounded-full bg-purple-600 ${speaking ? "animate-pulse" : ""}`}
            />
            <span
              className={`h-[4px] w-[4px] rounded-full bg-purple-600 ${speaking ? "animate-pulse" : ""}`}
            />
          </span>
        </div>

        <div className="flex items-center gap-[2px] h-5">
          {bars.slice(3).map((height, i) => (
            <div
              key={`r-${i}`}
              className="w-[3px] rounded-full bg-emerald-400"
              style={{
                height: speaking ? `${height * 100}%` : "30%",
                transition: speaking ? "height 80ms" : "height 300ms",
              }}
            />
          ))}
        </div>
      </div>

      {streamedStatus && (
        <span className="text-[10px] text-zinc-300 max-w-[160px] truncate bg-zinc-900/90 px-2 py-0.5 rounded-full backdrop-blur-sm border border-zinc-700/50">
          {streamedStatus}
        </span>
      )}
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { connectSocket } from "../lib/ws";
import type { Socket } from "socket.io-client";

export type RuntimeEvent = {
  event: string;
  data: Record<string, unknown>;
};

export function useEventReceiver(events?: string[]) {
  const [received, setReceived] = useState<RuntimeEvent[]>([]);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = connectSocket();

    socketRef.current = socket;

    const handler = (raw: RuntimeEvent | string) => {
      let parsed: RuntimeEvent;

      try {
        parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      } catch {
        return;
      }

      if (!parsed || typeof parsed.event !== "string") {
        return;
      }

      if (!parsed.data) {
        parsed = { ...parsed, data: {} };
      }

      setReceived((prev) => [...prev, parsed]);
    };

    if (events?.length) {
      for (const event of events) {
        socket.on(event, handler);
      }
    } else {
      socket.onAny((_event, payload) => {
        handler(payload);
      });
    }

    return () => {
      if (events?.length) {
        for (const event of events) {
          socket.off(event, handler);
        }
      } else {
        socket.offAny();
      }

      socketRef.current = null;
    };
  }, [events?.join(",")]);

  const clear = useCallback(() => {
    setReceived([]);
  }, []);

  const clearEvent = useCallback((eventName: string) => {
    setReceived((prev) => prev.filter((e) => e.event !== eventName));
  }, []);

  return {
    events: received,
    clear,
    clearEvent,
  };
}

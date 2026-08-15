import { useCallback, useEffect, useRef, useState } from "react";
import { connectSocket } from "../lib/ws";
import type { Socket } from "socket.io-client";

export type RuntimeEvent = {
  type: string;
  data: Record<string, unknown>;
};

export function useEventReceiver(events?: string[]) {
  const [received, setReceived] = useState<RuntimeEvent[]>([]);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = connectSocket();

    socketRef.current = socket;

    const handler = (raw: RuntimeEvent | string) => {
      let event: RuntimeEvent;

      try {
        event = typeof raw === "string" ? JSON.parse(raw) : raw;
      } catch {
        return;
      }

      if (!event || typeof event.type !== "string") {
        return;
      }

      setReceived((prev) => [...prev, event]);
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

  const clearType = useCallback((type: string) => {
    setReceived((prev) => prev.filter((event) => event.type !== type));
  }, []);

  return {
    events: received,
    clear,
    clearType,
  };
}

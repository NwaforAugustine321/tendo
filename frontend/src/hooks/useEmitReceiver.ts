import { useCallback, useEffect, useRef, useState } from "react";

import type { Socket } from "socket.io-client";

import { connectSocket } from "../lib/ws";

type SocketPayload = Record<string, unknown>;

export function useEventReceiver(events?: string[]) {
  const [received, setReceived] = useState<Record<string, any> | null | any>(
    null,
  );

  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = connectSocket();

    socketRef.current = socket;

    const listeners = new Map<string, (payload: SocketPayload) => void>();

    for (const eventName of events ?? []) {
      const listener = (payload: SocketPayload) => {
        setReceived(payload.data);
      };

      listeners.set(eventName, listener);

      socket.on(eventName, listener);
    }

    return () => {
      for (const [eventName, listener] of listeners) {
        socket.off(eventName, listener);
      }

      socketRef.current = null;
    };
  }, [events?.join(",")]);

  const clear = useCallback(() => {
    setReceived(null);
  }, []);

  const clearEvent = useCallback((eventName: string) => {
    setReceived((current) => {
      if (current?.event === eventName) {
        return null;
      }

      return current;
    });
  }, []);

  return {
    event: received,
    clear,
    clearEvent,
  };
}

import { useEffect, useRef, useState } from "react";

import { useEventReceiver, type RuntimeEvent } from "./useEmitReceiver";

type RuntimePresence = {
  text: string;
  event: string | null;
};

type UseAgentSessionStatusState = {
  events: RuntimeEvent[];
  presence: RuntimePresence;
};

function getEventType(event: RuntimeEvent): string | null {
  const data = event.data;

  if (typeof data?.type === "string") {
    return data.type;
  }

  return event.event || null;
}

function getPresenceText(event: RuntimeEvent): string {
  const data = event.data;

  if (data?.type !== "voice.presence" && data?.type !== "text.presence") {
    return "";
  }

  const payload = data.payload;

  if (!payload || typeof payload !== "object") {
    return "";
  }

  const message = (payload as Record<string, unknown>).message;

  return typeof message === "string" ? message : "";
}

export function useAgentSessionStatus(
  events?: string[],
): UseAgentSessionStatusState & {
  clear: () => void;
  clearEvent: (eventName: string) => void;
} {
  const {
    events: receivedEvents,
    clear: clearReceivedEvents,
    clearEvent: clearReceivedEvent,
  } = useEventReceiver(events);

  const [presence, setPresence] = useState<RuntimePresence>({
    text: "",
    event: null,
  });

  const processedCountRef = useRef(0);

  useEffect(() => {
    const newEvents = receivedEvents.slice(processedCountRef.current);

    if (!newEvents.length) {
      return;
    }

    let nextPresence = presence;

    for (const event of newEvents) {
      const type = getEventType(event);

      if (type !== "voice.presence" && type !== "text.presence") {
        continue;
      }

      const text = getPresenceText(event);

      if (!text) {
        continue;
      }

      const current = nextPresence.text;

      if (!current) {
        nextPresence = {
          text,
          event: type,
        };

        continue;
      }

      if (text.startsWith(current)) {
        nextPresence = {
          text,
          event: type,
        };

        continue;
      }

      nextPresence = {
        text: current + text,
        event: type,
      };
    }

    if (nextPresence !== presence) {
      setPresence(nextPresence);
    }

    processedCountRef.current = receivedEvents.length;
  }, [receivedEvents]);

  const clear = () => {
    setPresence({
      text: "",
      event: null,
    });

    processedCountRef.current = 0;

    clearReceivedEvents();
  };

  const clearEvent = (eventName: string) => {
    clearReceivedEvent(eventName);

    if (eventName === "voice.presence" || eventName === "text.presence") {
      setPresence({
        text: "",
        event: null,
      });

      processedCountRef.current = 0;
    }
  };

  return {
    events: receivedEvents,
    presence,
    clear,
    clearEvent,
  };
}

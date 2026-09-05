import { useCallback, useEffect, useRef, useState } from "react";

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
    let shouldReset = false;

    for (const event of newEvents) {
      /*
       * "message" is the Socket.IO response event.
       *
       * Once it arrives, the current presence is complete.
       */
      if (event.event === "message") {
        shouldReset = true;
        continue;
      }

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

    if (shouldReset) {
      if (presence.text || presence.event) {
        setPresence({
          text: "",
          event: null,
        });
      }
    } else if (
      nextPresence.text !== presence.text ||
      nextPresence.event !== presence.event
    ) {
      setPresence(nextPresence);
    }

    processedCountRef.current = receivedEvents.length;
  }, [receivedEvents, presence]);

  const clear = useCallback(() => {
    setPresence((current) => {
      if (!current.text && !current.event) {
        return current;
      }

      return {
        text: "",
        event: null,
      };
    });

    processedCountRef.current = receivedEvents.length;

    clearReceivedEvents();
  }, [clearReceivedEvents, receivedEvents.length]);

  const clearEvent = useCallback(
    (eventName: string) => {
      clearReceivedEvent(eventName);

      if (
        eventName === "voice.presence" ||
        eventName === "text.presence" ||
        eventName === "message"
      ) {
        setPresence((current) => {
          if (!current.text && !current.event) {
            return current;
          }

          return {
            text: "",
            event: null,
          };
        });

        processedCountRef.current = receivedEvents.length;
      }
    },
    [clearReceivedEvent, receivedEvents.length],
  );

  return {
    events: receivedEvents,
    presence,
    clear,
    clearEvent,
  };
}

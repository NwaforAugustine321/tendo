import { useEffect, useMemo, useRef } from "react";

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
  const data: any = event.data;

  if (data?.type === "voice.presence" || data?.type === "text.presence") {
    const message = data?.payload?.message;

    if (typeof message === "string") {
      return message;
    }
  }

  return "";
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

  const presenceRef = useRef<RuntimePresence>({
    text: "",
    event: null,
  });

  const processedCountRef = useRef(0);

  useEffect(() => {
    const newEvents = receivedEvents.slice(processedCountRef.current);

    if (!newEvents.length) {
      return;
    }

    for (const event of newEvents) {
      const type = getEventType(event);

      if (type !== "voice.presence" && type !== "text.presence") {
        continue;
      }

      const text = getPresenceText(event);

      if (!text) {
        continue;
      }

      const current = presenceRef.current.text;

      if (!current) {
        presenceRef.current = {
          text,
          event: type,
        };

        continue;
      }

      if (text.startsWith(current)) {
        presenceRef.current = {
          text,
          event: type,
        };

        continue;
      }

      presenceRef.current = {
        text: current + text,
        event: type,
      };
    }

    processedCountRef.current = receivedEvents.length;
  }, [receivedEvents]);

  const presence = useMemo<RuntimePresence>(() => {
    return presenceRef.current;
  }, [receivedEvents]);

  const clear = () => {
    presenceRef.current = {
      text: "",
      event: null,
    };

    processedCountRef.current = 0;

    clearReceivedEvents();
  };

  const clearEvent = (eventName: string) => {
    clearReceivedEvent(eventName);

    if (eventName === "voice.presence" || eventName === "text.presence") {
      presenceRef.current = {
        text: "",
        event: null,
      };

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

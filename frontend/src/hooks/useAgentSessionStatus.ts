import { useCallback, useEffect, useState } from "react";

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

  useEffect(() => {
    if (!receivedEvents.length) {
      return;
    }

    let nextPresence: RuntimePresence | null = null;
    let shouldReset = false;

    for (const event of receivedEvents) {
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

      if (!nextPresence?.text) {
        nextPresence = {
          text,
          event: type,
        };

        continue;
      }

      if (text.startsWith(nextPresence.text)) {
        nextPresence = {
          text,
          event: type,
        };

        continue;
      }

      nextPresence = {
        text: nextPresence.text + text,
        event: type,
      };
    }

    if (shouldReset) {
      setPresence((current) => {
        if (!current.text && !current.event) {
          return current;
        }

        return {
          text: "",
          event: null,
        };
      });
    } else if (nextPresence) {
      setPresence((current) => {
        if (
          current.text === nextPresence!.text &&
          current.event === nextPresence!.event
        ) {
          return current;
        }

        return nextPresence!;
      });
    }

    clearReceivedEvents();
  }, [receivedEvents, clearReceivedEvents]);

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

    clearReceivedEvents();
  }, [clearReceivedEvents]);

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
      }
    },
    [clearReceivedEvent],
  );

  return {
    events: receivedEvents,
    presence,
    clear,
    clearEvent,
  };
}

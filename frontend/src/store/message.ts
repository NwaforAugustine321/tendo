import { create } from "zustand";

import type { RuntimeEvent } from "../hooks/useEmitReceiver";

export type MessagePresence = {
  text: string;
  event: "text.presence" | null;
};

export type MessageTranscript = {
  text: string;
  event: "voice.transcript";
  data: RuntimeEvent;
};

export type MessageResponse = {
  text: string;
  event: "message" | "voice.response";
  data: RuntimeEvent;
};

type MessageState = {
  events: RuntimeEvent[];
  presence: MessagePresence;
  transcript: MessageTranscript | null;
  response: MessageResponse | null;

  addEvents: (events: RuntimeEvent[]) => void;
  clear: () => void;
  clearEvent: (eventName: string) => void;
};

function getEventType(event: RuntimeEvent): string | null {
  const type = event.data?.type;

  return typeof type === "string" ? type : null;
}

function getPayload(event: RuntimeEvent): Record<string, unknown> | null {
  const payload = event.data?.payload;

  if (!payload || typeof payload !== "object") {
    return null;
  }

  return payload as Record<string, unknown>;
}

function getPresenceText(event: RuntimeEvent): string {
  if (getEventType(event) !== "text.presence") {
    return "";
  }

  const payload = getPayload(event);
  const message = payload?.message;

  return typeof message === "string" ? message : "";
}

function getTranscript(event: RuntimeEvent): MessageTranscript | null {
  if (getEventType(event) !== "voice.transcript") {
    return null;
  }

  const payload = getPayload(event);
  const message = payload?.message;

  if (typeof message !== "string" || !message) {
    return null;
  }

  return {
    text: message,
    event: "voice.transcript",
    data: event,
  };
}

function getResponse(event: RuntimeEvent): MessageResponse | null {
  const type = getEventType(event);

  if (type !== "message" && type !== "voice.response") {
    return null;
  }

  const payload = getPayload(event);
  const text = payload?.message;

  if (typeof text !== "string" || !text) {
    return null;
  }

  return {
    text,
    event: type,
    data: event,
  };
}

function buildPresence(events: RuntimeEvent[]): MessagePresence {
  let text = "";

  for (const event of events) {
    const presenceText = getPresenceText(event);

    if (!presenceText) {
      continue;
    }

    if (!text) {
      text = presenceText;
      continue;
    }

    if (presenceText.startsWith(text)) {
      text = presenceText;
      continue;
    }

    if (text.startsWith(presenceText)) {
      continue;
    }

    text += presenceText;
  }

  return {
    text,
    event: text ? "text.presence" : null,
  };
}

export const useMessageStore = create<MessageState>((set) => ({
  events: [],

  presence: {
    text: "",
    event: null,
  },

  transcript: null,

  response: null,

  addEvents: (incomingEvents) => {
    if (!incomingEvents.length) {
      return;
    }

    set((state) => {
      let transcript = state.transcript;
      let response = state.response;

      for (const event of incomingEvents) {
        const nextTranscript = getTranscript(event);

        if (nextTranscript) {
          transcript = nextTranscript;
        }

        const nextResponse = getResponse(event);

        if (nextResponse) {
          response = nextResponse;
        }
      }

      const events = [...state.events, ...incomingEvents];

      return {
        events,
        presence: buildPresence(events),
        transcript,
        response,
      };
    });
  },

  clear: () => {
    set({
      events: [],
      presence: {
        text: "",
        event: null,
      },
      transcript: null,
      response: null,
    });
  },

  clearEvent: (eventName) => {
    set((state) => {
      const events = state.events.filter(
        (event) => getEventType(event) !== eventName,
      );

      if (eventName === "text.presence") {
        return {
          events,
          presence: {
            text: "",
            event: null,
          },
        };
      }

      if (eventName === "voice.transcript") {
        return {
          events,
          transcript: null,
        };
      }

      if (eventName === "message" || eventName === "voice.response") {
        return {
          events,
          response: null,
        };
      }

      return {
        events,
      };
    });
  },
}));

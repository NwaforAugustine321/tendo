import { create } from "zustand";

import { EventType } from "../types/event";

type EventTypeValue = (typeof EventType)[keyof typeof EventType];

export type MessagePresence = {
  content: string;
  event: typeof EventType.TextPresence | null;
};

export type MessageTranscript = {
  content: string;
  event: typeof EventType.VoiceTranscript;
  data: Record<string, any>;
};

export type MessageResponse = {
  content: string;
  event: typeof EventType.Message | typeof EventType.VoiceResponse;
  data: Record<string, any>;
};

type MessageState = {
  events: Record<string, any>[];

  presence: MessagePresence | null;

  transcript: MessageTranscript | null;

  response: MessageResponse | null;

  /*
   * Reasoning is shared because multiple components
   * can call useMessage() at the same time.
   */
  reasoning: boolean;

  addEvents: (events: Record<string, any>[]) => void;

  startReasoning: () => void;

  stopReasoning: () => void;

  clear: () => void;

  clearEvent: (eventName: EventTypeValue) => void;
};

function getEventType(event: Record<string, any>): EventTypeValue | null {
  const type = event?.type;

  if (
    typeof type !== "string" ||
    !Object.values(EventType).includes(type as EventTypeValue)
  ) {
    return null;
  }

  return type as EventTypeValue;
}

function getPayload(event: Record<string, any>): Record<string, unknown> {
  const payload = event?.payload;

  if (!payload || typeof payload !== "object") {
    return {};
  }

  return payload as Record<string, unknown>;
}

function getPresenceText(event: Record<string, any>): MessagePresence | null {
  if (getEventType(event) !== EventType.TextPresence) {
    return null;
  }

  const payload = getPayload(event);

  const message = payload?.message;

  if (typeof message !== "string" || !message) {
    return null;
  }

  return {
    content: message,
    event: EventType.TextPresence,
  };
}

function getTranscript(event: Record<string, any>): MessageTranscript | null {
  if (getEventType(event) !== EventType.VoiceTranscript) {
    return null;
  }

  const payload = getPayload(event);

  const message = payload?.message;

  if (typeof message !== "string" || !message) {
    return null;
  }

  return {
    content: message,
    event: EventType.VoiceTranscript,
    data: event,
  };
}

function getResponse(event: Record<string, any>): MessageResponse | null {
  const type = getEventType(event);

  if (type !== EventType.Message && type !== EventType.VoiceResponse) {
    return null;
  }

  const payload = getPayload(event);

  const message = payload?.message;

  if (typeof message !== "string" || !message) {
    return null;
  }

  return {
    content: message,
    event: type,
    data: event,
  };
}

export const useMessageStore = create<MessageState>((set) => ({
  events: [],

  presence: null,

  transcript: null,

  response: null,

  reasoning: false,

  addEvents: (incomingEvents) => {
    if (!incomingEvents.length) {
      return;
    }

    set((state) => {
      let transcript = state.transcript;

      let response = state.response;

      let presence = state.presence;

      for (const event of incomingEvents) {
        const nextTranscript = getTranscript(event);

        if (nextTranscript) {
          transcript = nextTranscript;
        }

        const nextPresence = getPresenceText(event);

        if (nextPresence) {
          presence = nextPresence;
        }

        const nextResponse = getResponse(event);

        if (nextResponse) {
          response = nextResponse;
        }
      }

      const events = [...state.events, ...incomingEvents];

      return {
        events,
        presence,
        transcript,
        response,
      };
    });
  },

  startReasoning: () => {
    set({
      reasoning: true,
    });
  },

  stopReasoning: () => {
    set({
      reasoning: false,
    });
  },

  clear: () => {
    set({
      events: [],
      presence: null,
      transcript: null,
      response: null,
      reasoning: false,
    });
  },

  clearEvent: (eventName) => {
    set((state) => {
      const events = state.events.filter(
        (event) => getEventType(event) !== eventName,
      );

      if (eventName === EventType.TextPresence) {
        return {
          events,
          presence: null,
        };
      }

      if (eventName === EventType.VoicePresence) {
        return {
          events,
        };
      }

      if (eventName === EventType.VoiceTranscript) {
        return {
          events,
          transcript: null,
        };
      }

      if (
        eventName === EventType.Message ||
        eventName === EventType.VoiceResponse
      ) {
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

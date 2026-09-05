import { useCallback, useEffect, useMemo } from "react";

import { useEventReceiver } from "./useEmitReceiver";
import { useMessageStore } from "../store/message";
import { useVoiceAgentStore } from "../store/voice";
import { EventType } from "../types/event";

type EventTypeValue = (typeof EventType)[keyof typeof EventType];

export type MessageInteractionMode = "text" | "listening" | "speaking";

export type MessageStatus = "idle" | "reasoning" | "listening" | "speaking";

const MESSAGE_EVENTS: EventTypeValue[] = [
  EventType.VoiceTranscript,
  EventType.VoicePresence,
  EventType.TextPresence,
  EventType.Message,
  EventType.VoiceResponse,
];

export function useMessage() {
  const {
    events,
    presence,
    response,
    transcript,
    reasoning,
    addEvents,
    clear,
    clearEvent,
    startReasoning,
    stopReasoning,
  } = useMessageStore();

  const {
    interactionMode: voiceInteractionMode,
    micActive,
    userSpeaking,
    agentSpeaking,
    connectionState,
    agentReady,
    errorMessage,
    startAgent,
    stopMic,
    stopAgent,
    sendPrompt,
    initAgent,
  } = useVoiceAgentStore();

  const { event: receivedEvent } = useEventReceiver(MESSAGE_EVENTS);

  useEffect(() => {
    if (!receivedEvent) {
      return;
    }

    addEvents([receivedEvent]);
  }, [receivedEvent, addEvents]);

  /*
   * START REQUEST
   *
   * Clear all transient events from the previous
   * request and start the shared reasoning lifecycle.
   */
  const startRequest = useCallback(() => {
    clearEvent(EventType.TextPresence);

    clearEvent(EventType.VoicePresence);

    clearEvent(EventType.VoiceResponse);

    clearEvent(EventType.Message);

    clearEvent(EventType.VoiceTranscript);

    startReasoning();
  }, [clearEvent, startReasoning]);

  const startTextRequest = useCallback(() => {
    startRequest();
  }, [startRequest]);

  /*
   * VOICE TRANSCRIPT
   *
   * A transcript means a new voice request has started.
   *
   * Start shared reasoning so every useMessage()
   * instance sees the same reasoning state.
   */
  useEffect(() => {
    if (!transcript?.content) {
      return;
    }

    clearEvent(EventType.TextPresence);

    clearEvent(EventType.VoicePresence);

    clearEvent(EventType.VoiceResponse);

    clearEvent(EventType.Message);

    startReasoning();
  }, [transcript?.content, clearEvent, startReasoning]);

  /*
   * PRESENCE
   *
   * Presence does not change the reasoning lifecycle.
   *
   * The presence itself is already stored in the shared
   * message store, so every useMessage() instance receives
   * the latest value.
   */
  useEffect(() => {
    if (!presence?.content) {
      return;
    }
  }, [presence?.content]);

  /*
   * FINAL RESPONSE
   *
   * A final message or voice response ends reasoning.
   */
  useEffect(() => {
    if (!response?.content) {
      return;
    }

    stopReasoning();

    clearEvent(EventType.TextPresence);

    clearEvent(EventType.VoicePresence);
  }, [response?.content, clearEvent, stopReasoning]);

  /*
   * VOICE SPEAKING COMPLETE
   */
  useEffect(() => {
    if (agentSpeaking) {
      return;
    }

    if (!micActive) {
      return;
    }

    if (voiceInteractionMode !== "speaking") {
      return;
    }

    clearEvent(EventType.TextPresence);

    clearEvent(EventType.VoicePresence);

    stopReasoning();
  }, [
    agentSpeaking,
    micActive,
    voiceInteractionMode,
    clearEvent,
    stopReasoning,
  ]);

  /*
   * MICROPHONE ACTIVE
   *
   * Once microphone mode is active, reasoning is no
   * longer the active state until a transcript arrives.
   */
  useEffect(() => {
    if (!micActive) {
      return;
    }

    stopReasoning();

    clearEvent(EventType.TextPresence);

    clearEvent(EventType.VoicePresence);
  }, [micActive, clearEvent, stopReasoning]);

  const interactionMode = useMemo<MessageInteractionMode>(() => {
    if (!micActive) {
      return "text";
    }

    if (agentSpeaking) {
      return "speaking";
    }

    return "listening";
  }, [micActive, agentSpeaking]);

  const status = useMemo<MessageStatus>(() => {
    if (agentSpeaking) {
      return "speaking";
    }

    if (reasoning) {
      return "reasoning";
    }

    if (micActive) {
      return "listening";
    }

    return "idle";
  }, [agentSpeaking, reasoning, micActive]);

  /*
   * STATUS TEXT
   *
   * This is now derived from shared Zustand state.
   *
   * Therefore every component calling useMessage()
   * receives the same live statusText.
   *
   * Example:
   *
   * Reasoning...
   *      ↓
   * Searching your knowledge...
   *      ↓
   * Analyzing the results...
   *      ↓
   * Preparing the response...
   */
  const statusText = useMemo(() => {
    if (agentSpeaking) {
      return "Speaking...";
    }

    if (reasoning && presence?.content) {
      return presence.content;
    }

    if (reasoning) {
      return "Reasoning...";
    }

    if (micActive) {
      return "Listening...";
    }

    return "";
  }, [agentSpeaking, presence?.content, reasoning, micActive]);

  const isVoiceMode =
    interactionMode === "listening" || interactionMode === "speaking";

  const isTextMode = interactionMode === "text";

  const isBusy = status === "reasoning" || status === "speaking";

  return {
    events,
    presence,
    response,
    transcript,

    interactionMode,
    status,
    statusText,

    isVoiceMode,
    isTextMode,
    isBusy,

    reasoning,

    micActive,
    userSpeaking,
    agentSpeaking,
    agentReady,
    connectionState,
    errorMessage,

    startAgent,
    stopMic,
    stopAgent,
    sendPrompt,
    initAgent,

    startTextRequest,
    startRequest,

    clear,
    clearEvent,
  };
}

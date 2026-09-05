import { useCallback, useEffect, useMemo, useState } from "react";

import { useEventReceiver } from "./useEmitReceiver";
import { useMessageStore } from "../store/message";
import { useVoiceAgentStore } from "../store/voice";

export type MessageInteractionMode = "text" | "listening" | "speaking";

export type MessageStatus = "idle" | "reasoning" | "listening" | "speaking";

export function useMessage() {
  const {
    events,
    presence,
    response,
    transcript,
    addEvents,
    clear,
    clearEvent,
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

  const [reasoning, setReasoning] = useState(false);

  const { event: receivedEvent } = useEventReceiver([
    "voice.transcript",
    "voice.presence",
    "text.presence",
    "message",
    "voice.response",
  ]);

  /*
   * Runtime events.
   */
  useEffect(() => {
    if (!receivedEvent) {
      return;
    }

    addEvents([receivedEvent]);
  }, [receivedEvent, addEvents]);

  /*
   * Start a completely new request.
   *
   * Clear transient state from the previous
   * request before entering reasoning.
   */
  const startRequest = useCallback(() => {
    clearEvent("text.presence");
    clearEvent("voice.presence");
    clearEvent("voice.response");
    clearEvent("message");
    clearEvent("voice.transcript");

    setReasoning(true);
  }, [clearEvent]);

  /*
   * Voice transcript means the user has
   * finished speaking and Tendo is now
   * processing the request.
   */
  useEffect(() => {
    if (!transcript) {
      return;
    }

    /*
     * A transcript starts a NEW voice request.
     *
     * Clear anything left over from the
     * previous request first.
     */
    clearEvent("text.presence");
    clearEvent("voice.presence");
    clearEvent("voice.response");
    clearEvent("message");

    setReasoning(true);
  }, [transcript, clearEvent]);

  /*
   * A final response ends reasoning.
   */
  useEffect(() => {
    if (!response) {
      return;
    }

    clearEvent("text.presence");
    clearEvent("voice.presence");

    setReasoning(false);
  }, [response, clearEvent]);

  /*
   * Agent finished speaking.
   *
   * Only applies to an active voice
   * interaction.
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

    clearEvent("text.presence");
    clearEvent("voice.presence");

    setReasoning(false);
  }, [agentSpeaking, micActive, voiceInteractionMode, clearEvent]);

  /*
   * Final voice response.
   */
  useEffect(() => {
    if (!response) {
      return;
    }

    if (response.event !== "voice.response") {
      return;
    }

    if (!micActive) {
      return;
    }

    setReasoning(false);

    clearEvent("text.presence");
    clearEvent("voice.presence");
  }, [response, micActive, clearEvent]);

  /*
   * Final text response.
   */
  useEffect(() => {
    if (!response) {
      return;
    }

    if (response.event !== "message") {
      return;
    }

    setReasoning(false);

    clearEvent("text.presence");
    clearEvent("voice.presence");
  }, [response, clearEvent]);

  /*
   * Start a text request.
   *
   * This clears the previous startup/
   * presence state first.
   */
  const startTextRequest = useCallback(() => {
    startRequest();
  }, [startRequest]);

  /*
   * Presence replaces the generic
   * "Reasoning..." state with the actual
   * runtime progress text.
   */
  useEffect(() => {
    if (!presence.text) {
      return;
    }

    setReasoning(false);
  }, [presence.text]);

  /*
   * Do NOT reset reasoning simply because
   * micActive is false.
   *
   * Text requests have micActive === false.
   */
  useEffect(() => {
    if (!micActive) {
      return;
    }

    setReasoning(false);

    clearEvent("text.presence");
    clearEvent("voice.presence");
  }, [micActive, clearEvent]);

  /*
   * Effective interaction mode.
   */
  const interactionMode: MessageInteractionMode = micActive
    ? agentSpeaking
      ? "speaking"
      : "listening"
    : "text";

  /*
   * Overall status.
   */
  const status = useMemo<MessageStatus>(() => {
    if (agentSpeaking) {
      return "speaking";
    }

    if (presence.text) {
      return "reasoning";
    }

    if (reasoning) {
      return "reasoning";
    }

    if (micActive) {
      return "listening";
    }

    return "idle";
  }, [agentSpeaking, presence.text, reasoning, micActive]);

  /*
   * Human-readable status.
   */
  const statusText = useMemo(() => {
    if (agentSpeaking) {
      return "Speaking...";
    }

    if (presence.text) {
      return presence.text;
    }

    if (reasoning) {
      return "Reasoning...";
    }

    if (micActive) {
      return "Listening...";
    }

    return "";
  }, [agentSpeaking, presence.text, reasoning, micActive]);

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

    clear,
    clearEvent,
  };
}

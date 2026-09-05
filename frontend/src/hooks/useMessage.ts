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
  } = useVoiceAgentStore();

  const [reasoning, setReasoning] = useState(false);

  const { events: receivedEvents } = useEventReceiver([
    "voice.transcript",
    "voice.presence",
    "text.presence",
    "message",
    "voice.response",
  ]);

  useEffect(() => {
    if (!receivedEvents.length) {
      return;
    }

    addEvents(receivedEvents);
  }, [receivedEvents, addEvents]);

  const interactionMode: MessageInteractionMode = voiceInteractionMode;

  /*
   * A voice transcript is the user's message.
   *
   * It starts the reasoning phase.
   */
  useEffect(() => {
    if (!transcript) {
      return;
    }

    clearEvent("text.presence");
    clearEvent("voice.response");

    setReasoning(true);
  }, [transcript, clearEvent]);

  /*
   * A final response ends reasoning.
   *
   * voice.response:
   *   Voice mode -> Listening...
   *
   * message:
   *   Text mode -> nothing
   */
  useEffect(() => {
    if (!response) {
      return;
    }

    clearEvent("text.presence");
    setReasoning(false);
  }, [response, clearEvent]);

  /*
   * Agent speaking is the voice TTS phase.
   *
   * Once speaking finishes, voice mode returns
   * to Listening...
   */
  useEffect(() => {
    if (agentSpeaking) {
      return;
    }

    if (!micActive) {
      return;
    }

    if (interactionMode !== "speaking") {
      return;
    }

    clearEvent("text.presence");
    setReasoning(false);
  }, [agentSpeaking, micActive, interactionMode, clearEvent]);

  /*
   * A voice response explicitly returns the voice
   * interaction to Listening...
   *
   * This happens only for voice.response.
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
  }, [response, micActive, clearEvent]);

  /*
   * A normal message is the text interaction response.
   *
   * It clears the reasoning state and leaves the
   * text interaction with no status.
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
  }, [response, clearEvent]);

  /*
   * Starting a text request enters reasoning.
   */
  const startTextRequest = useCallback(() => {
    clearEvent("text.presence");
    clearEvent("voice.response");

    setReasoning(true);
  }, [clearEvent]);

  /*
   * Presence replaces the initial Reasoning... state.
   */
  useEffect(() => {
    if (!presence.text) {
      return;
    }

    setReasoning(false);
  }, [presence.text]);

  /*
   * Microphone activation starts Listening...
   */
  useEffect(() => {
    if (!micActive) {
      return;
    }

    setReasoning(false);
    clearEvent("text.presence");
  }, [micActive, clearEvent]);

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

    startTextRequest,

    clear,
    clearEvent,
  };
}

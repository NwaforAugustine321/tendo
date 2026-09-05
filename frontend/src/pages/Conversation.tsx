import { useCallback, useEffect, useRef, useState } from "react";

import { ConversationPage, type MessageItem } from "../components/containers";

import { useMessage } from "../hooks/useMessage";

import { useBusinessStore } from "../store/business";
import { useWorkspaceStore } from "../store/workspace";

import { connectSocket } from "../lib/ws";

import { EventType } from "../types/event";

type Props = {
  initialMessages?: MessageItem[];
  sessionId?: string;
  fullScreen?: boolean;
  transparentBg?: boolean;
  recordId?: string;
  onFirstMessage?: () => void;
};

export function Conversation({
  initialMessages,
  sessionId,
  fullScreen = false,
  transparentBg = false,
  recordId,
  onFirstMessage,
}: Props) {
  const [messages, setMessages] = useState<MessageItem[]>(
    initialMessages ?? [],
  );

  const { currentProfile } = useBusinessStore();

  const businessId = currentProfile?.id ?? "";

  /*
   * useMessage owns runtime state
   * and voice lifecycle.
   */
  const {
    isBusy,
    statusText,
    transcript,
    response,
    startTextRequest,
    initAgent,
    micActive,
    startAgent,
    stopMic,
  } = useMessage();

  const pendingMsg = useWorkspaceStore((state) => state.pendingChatMessage);

  const pendingSentRef = useRef<string | null>(null);

  /*
   * Prevent the same transcript
   * from being appended twice.
   */
  const processedTranscriptRef = useRef<object | null>(null);

  /*
   * Prevent the same response
   * from being appended twice.
   */
  const processedResponseRef = useRef<object | null>(null);

  /*
   * Keep persisted messages synchronized
   * with ChatPanel.
   */
  useEffect(() => {
    setMessages(initialMessages ?? []);

    processedTranscriptRef.current = null;

    processedResponseRef.current = null;
  }, [initialMessages]);

  /*
   * Reset runtime message consumption
   * when the active session changes.
   */
  useEffect(() => {
    processedTranscriptRef.current = null;

    processedResponseRef.current = null;

    pendingSentRef.current = null;

    setMessages(initialMessages ?? []);
  }, [sessionId, initialMessages]);

  /*
   * Add a voice transcript to the
   * conversation as a user message.
   */
  useEffect(() => {
    if (!transcript) {
      return;
    }

    if (processedTranscriptRef.current === transcript.data) {
      return;
    }

    processedTranscriptRef.current = transcript.data;

    setMessages((previous) => [
      ...previous,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: transcript.content,
        type: "text",
      },
    ]);
  }, [transcript]);

  /*
   * Add the final AI response to
   * the conversation.
   *
   * Handles both:
   *
   * - message
   * - voice.response
   */
  useEffect(() => {
    if (!response) {
      return;
    }

    if (processedResponseRef.current === response.data) {
      return;
    }

    processedResponseRef.current = response.data;

    setMessages((previous) => [
      ...previous,
      {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.content,
        type: "text",
        stream: false,
      },
    ]);
  }, [response]);

  /*
   * Send a text request through the
   * existing application socket.
   *
   * This does not own socket lifecycle.
   */
  const sendChatText = useCallback(
    (text: string): boolean => {
      if (!text) {
        return false;
      }
      const message = text?.trim();

      if (!message || !businessId || !sessionId) {
        return false;
      }

      try {
        const socket = connectSocket();

        if (!socket.connected) {
          return false;
        }

        socket.emit("message", {
          type: "text",
          payload: {
            content: message,
            business_id: businessId,
            session_id: sessionId,
            record_id: recordId ?? "",
          },
        });

        return true;
      } catch {
        return false;
      }
    },
    [businessId, sessionId, recordId],
  );

  /*
   * Resolve radio option IDs to
   * human-readable labels.
   */
  const findOptionContext = useCallback(
    (
      optionId: string,
    ): {
      id: string;
      name: string;
      label: string;
      description?: string;
    } | null => {
      for (let index = messages.length - 1; index >= 0; index--) {
        const message = messages[index];

        if (message.type !== "input" || !message.inputSpec?.fields) {
          continue;
        }

        for (const field of message.inputSpec.fields) {
          if (field.type !== "radio" || !field.options) {
            continue;
          }

          const found: any = field.options.find(
            (option) => option.id === optionId,
          );

          if (found) {
            return found;
          }
        }
      }

      return null;
    },
    [messages],
  );

  /*
   * Main text request.
   */
  const handleSendText = useCallback(
    (text: string) => {
      if (!text) {
        return;
      }
      const message = text?.trim();

      if (!message || !businessId || !sessionId) {
        return;
      }

      const optionContext = findOptionContext(message);

      const displayText = optionContext?.label ?? message;

      /*
       * Verify transport before
       * changing the conversation.
       */
      const sent = sendChatText(message);

      if (!sent) {
        return;
      }

      setMessages((previous) => [
        ...previous,
        {
          id: `user-${Date.now()}`,
          role: "user",
          content: displayText,
          type: "text",
        },
      ]);

      /*
       * Enter reasoning state.
       */
      startTextRequest();

      if (onFirstMessage && messages.length === 0) {
        onFirstMessage();
      }
    },
    [
      businessId,
      sessionId,
      findOptionContext,
      sendChatText,
      startTextRequest,
      onFirstMessage,
      messages.length,
    ],
  );

  /*
   * Consume a pending message from
   * HomeAskTendo.
   */
  useEffect(() => {
    if (!pendingMsg || pendingMsg === pendingSentRef.current) {
      return;
    }

    if (!businessId || !sessionId) {
      return;
    }

    pendingSentRef.current = pendingMsg;

    handleSendText(pendingMsg);

    useWorkspaceStore.getState().setPendingChatMessage(null);
  }, [pendingMsg, businessId, sessionId, handleSendText]);

  /*
   * Initialize LiveKit for this
   * exact business/session pair.
   */
  useEffect(() => {
    if (!businessId || !sessionId) {
      return;
    }

    let cancelled = false;

    const initialize = async () => {
      try {
        await initAgent(businessId, sessionId);
      } catch {
        /*
         * The voice store owns
         * the error state.
         */
        if (cancelled) {
          return;
        }
      }
    };

    void initialize();

    return () => {
      cancelled = true;
    };
  }, [businessId, sessionId, initAgent]);

  /*
   * Voice toggle.
   */
  const handleVoiceToggle = useCallback(async () => {
    if (micActive) {
      stopMic();
      return;
    }

    try {
      await startAgent();
    } catch {
      /*
       * Voice store owns
       * the error state.
       */
    }
  }, [micActive, startAgent, stopMic]);

  /*
   * Input option selection.
   */
  const handleOptionSelect = useCallback(
    (optionId: string) => {
      handleSendText(optionId);
    },
    [handleSendText],
  );

  return (
    <ConversationPage
      messages={messages}
      isTyping={isBusy}
      statusText={statusText}
      fullScreen={fullScreen}
      transparentBg={transparentBg}
      onSendText={handleSendText}
      onOptionSelect={handleOptionSelect}
      onConfirm={() => handleOptionSelect(EventType.Message)}
      onModify={() => {}}
      onCancel={() => handleOptionSelect("cancel")}
      onRevert={() => {}}
      onContinueFromHere={() => {}}
    />
  );
}

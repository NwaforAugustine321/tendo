import { useCallback, useEffect, useRef, useState } from "react";

import { ConversationPage, type MessageItem } from "../components/containers";

import { useMessage } from "../hooks/useMessage";

import { useBusinessStore } from "../store/business";
import { useWorkspaceStore } from "../store/workspace";

import { connectSocket } from "../lib/ws";

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
   * useMessage is the single owner of:
   *
   * - runtime events
   * - presence
   * - transcript
   * - response
   * - reasoning state
   * - voice lifecycle
   */
  const {
    events,
    status,
    startTextRequest,
    initAgent,
    micActive,
    startAgent,
    stopMic,
  } = useMessage();

  const pendingMsg = useWorkspaceStore((state) => state.pendingChatMessage);

  const pendingSentRef = useRef<string | null>(null);

  /*
   * Number of runtime events already
   * consumed by this Conversation.
   */
  const processedEventCountRef = useRef(0);

  /*
   * Session currently represented by
   * this Conversation instance.
   */
  const mountedSessionRef = useRef<string | undefined>(sessionId);

  /*
   * Keep persisted messages synchronized
   * with ChatPanel.
   */
  useEffect(() => {
    setMessages(initialMessages ?? []);
  }, [initialMessages]);

  /*
   * Detect a session boundary.
   *
   * Runtime events belonging to the
   * previous session must never be
   * replayed into this session.
   */
  useEffect(() => {
    if (mountedSessionRef.current === sessionId) {
      return;
    }

    mountedSessionRef.current = sessionId;

    /*
     * Ignore all events that existed
     * before this session became active.
     */
    processedEventCountRef.current = events.length;

    setMessages(initialMessages ?? []);

    pendingSentRef.current = null;
  }, [sessionId, initialMessages, events.length]);

  /*
   * Convert only NEW runtime events
   * into conversation messages.
   */
  useEffect(() => {
    if (!events.length) {
      return;
    }

    /*
     * The message store may have been
     * cleared while this component
     * remained mounted.
     */
    if (processedEventCountRef.current > events.length) {
      processedEventCountRef.current = events.length;

      return;
    }

    const startIndex = processedEventCountRef.current;

    const newEvents = events.slice(startIndex);

    if (!newEvents.length) {
      return;
    }

    /*
     * Advance the cursor BEFORE
     * updating React state so the same
     * events cannot be consumed twice.
     */
    processedEventCountRef.current = events.length;

    const newMessages: MessageItem[] = [];

    for (const event of newEvents) {
      const type = event.data?.type;

      if (
        type !== "voice.transcript" &&
        type !== "message" &&
        type !== "voice.response"
      ) {
        continue;
      }

      const payload = event.data?.payload;

      if (!payload || typeof payload !== "object") {
        continue;
      }

      const payloadRecord = payload as Record<string, unknown>;

      const content =
        typeof payloadRecord.content === "string"
          ? payloadRecord.content
          : typeof payloadRecord.message === "string"
            ? payloadRecord.message
            : "";

      if (!content.trim()) {
        continue;
      }

      if (type === "voice.transcript") {
        newMessages.push({
          id: `user-${Date.now()}-${newMessages.length}`,
          role: "user",
          content,
          type: "text",
        });

        continue;
      }

      newMessages.push({
        id: `assistant-${Date.now()}-${newMessages.length}`,
        role: "assistant",
        content,
        type: "text",
        stream: true,
      });
    }

    if (!newMessages.length) {
      return;
    }

    setMessages((previous) => [...previous, ...newMessages]);
  }, [events]);

  /*
   * Send a text request through the
   * existing application socket.
   *
   * This does NOT create or own the
   * socket lifecycle.
   */
  const sendChatText = useCallback(
    (text: string): boolean => {
      const message = text.trim();

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

          const found = field.options.find((option) => option.id === optionId);

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
      const message = text.trim();

      if (!message || !businessId || !sessionId) {
        return;
      }

      const optionContext = findOptionContext(message);

      const displayText = optionContext?.label ?? message;

      /*
       * Verify transport before
       * modifying the conversation UI.
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
       * Enter:
       *
       * Reasoning...
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
   *
   * IMPORTANT:
   * Catch the rejected promise.
   * The voice store intentionally
   * rethrows initialization errors.
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
         * useMessage / voice store
         * already exposes the error
         * through its state.
         *
         * Do not allow an async
         * initialization rejection
         * to become an unhandled
         * promise rejection.
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
       * Voice store owns the
       * error state.
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

  /*
   * ConversationPage only needs
   * message state and interaction
   * callbacks.
   */
  return (
    <ConversationPage
      messages={messages}
      isTyping={status === "reasoning" || status === "speaking"}
      fullScreen={fullScreen}
      transparentBg={transparentBg}
      onSendText={handleSendText}
      onOptionSelect={handleOptionSelect}
      onConfirm={() => handleOptionSelect("confirm")}
      onModify={() => {}}
      onCancel={() => handleOptionSelect("cancel")}
      onRevert={() => {}}
      onContinueFromHere={() => {}}
    />
  );
}

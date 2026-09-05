import { useCallback, useEffect, useRef, useState } from "react";

import { ConversationPage, type MessageItem } from "../components/containers";

import { useMessage } from "../hooks/useMessage";

import { useBusinessStore } from "../store/business";

import { useWorkspaceStore } from "../store/workspace";

import { connectSocket, disconnectSocket } from "../lib/ws";

type Props = {
  initialMessages?: MessageItem[];
  sessionTitle?: string;
  sessionId?: string;
  fullScreen?: boolean;
  showHeader?: boolean;
  transparentBg?: boolean;
  flipCharacter?: boolean;
  characterRightOffset?: number;
  recordId?: string;
  onFirstMessage?: () => void;
};

export function Conversation({
  initialMessages,
  sessionTitle,
  sessionId,
  fullScreen = false,
  showHeader = false,
  transparentBg = false,
  flipCharacter = false,
  characterRightOffset = 0,
  recordId,
  onFirstMessage,
}: Props) {
  const [messages, setMessages] = useState<MessageItem[]>(
    initialMessages ?? [],
  );

  const [socketConnected, setSocketConnected] = useState(true);

  const [wakeActive, setWakeActive] = useState(false);

  const { currentProfile } = useBusinessStore();

  const businessId = currentProfile?.id ?? "";

  const {
    statusText,
    isVoiceMode,
    micActive,
    agentSpeaking,
    connectionState,
    startTextRequest,
    startAgent,
    stopMic,
    initAgent,
    clearEvent,
  } = useMessage();

  const { sendPrompt } = useMessage();

  const pendingMsg = useWorkspaceStore((state) => state.pendingChatMessage);

  const pendingSentRef = useRef<string | null>(null);

  const isConnected =
    connectionState === "ready" ||
    connectionState === "listening" ||
    connectionState === "speaking";

  const isListening = connectionState === "listening";

  const isSpeaking = connectionState === "speaking";

  const voiceLoading =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent";

  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  /*
   * The message lifecycle is owned by useMessage.
   *
   * Conversation only subscribes to the resulting
   * events for rendering the conversation history.
   */
  useEffect(() => {
    const socket = connectSocket();

    const onConnect = () => {
      setSocketConnected(true);
    };

    const onDisconnect = () => {
      setSocketConnected(false);
    };

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);

    setSocketConnected(socket.connected);

    return () => {
      socket.off("connect", onConnect);

      socket.off("disconnect", onDisconnect);

      disconnectSocket();
    };
  }, []);

  /*
   * Convert the events owned by useMessage into
   * conversation UI messages.
   */
  const { events } = useMessage();

  useEffect(() => {
    if (!events.length) {
      return;
    }

    const latest = events[events.length - 1];

    const type = latest.data?.type;

    const payload: any = latest.data?.payload;

    if (!payload || typeof payload !== "object") {
      return;
    }

    const content: any =
      typeof payload.content === "string"
        ? payload.content
        : typeof payload.message === "string"
          ? payload.message
          : "";

    if (!content) {
      return;
    }

    if (type === "voice.transcript") {
      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: "user",
          content,
          type: "text",
        },
      ]);

      return;
    }

    if (type === "message" || type === "voice.response") {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content,
          type: "text",
          stream: true,
        },
      ]);
    }
  }, [events]);

  const sendChatText = useCallback(
    (text: string) => {
      if (!text.trim() || !businessId || !sessionId) {
        return;
      }

      const socket = connectSocket();

      socket.emit("message", {
        type: "text",
        payload: {
          content: text,
          business_id: businessId,
          session_id: sessionId,
          record_id: recordId || "",
        },
      });
    },
    [businessId, sessionId, recordId],
  );

  const findOptionContext = useCallback(
    (
      optionId: string,
    ): {
      id: string;
      name: string;
      label: string;
      description?: string;
    } | null => {
      for (let i = messages.length - 1; i >= 0; i--) {
        const msg = messages[i];

        if (msg.type !== "input" || !msg.inputSpec?.fields) {
          continue;
        }

        for (const field of msg.inputSpec.fields) {
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

  const handleSendText = useCallback(
    (text: string) => {
      if (!text.trim()) {
        return;
      }

      const optionContext = findOptionContext(text);

      const displayText = optionContext?.label || text;

      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: "user",
          content: displayText,
          type: "text",
        },
      ]);

      startTextRequest();

      sendChatText(text);

      if (onFirstMessage && messages.length === 0) {
        onFirstMessage();
      }
    },
    [
      findOptionContext,
      messages.length,
      onFirstMessage,
      sendChatText,
      startTextRequest,
    ],
  );

  /*
   * HomeAskTendo sends text requests through the
   * workspace pending-message mechanism.
   */
  useEffect(() => {
    if (!pendingMsg || pendingMsg === pendingSentRef.current) {
      return;
    }

    pendingSentRef.current = pendingMsg;

    handleSendText(pendingMsg);

    useWorkspaceStore.getState().setPendingChatMessage(null);
  }, [pendingMsg, handleSendText]);

  /*
   * Initialize the LiveKit voice session once
   * the selected business/session is available.
   */
  useEffect(() => {
    if (!businessId || !sessionId) {
      return;
    }

    void initAgent(businessId, sessionId);
  }, [businessId, sessionId, initAgent]);

  /*
   * Keep the wake state synchronized with the
   * actual voice interaction state.
   */
  useEffect(() => {
    if (isConnected && micActive) {
      setWakeActive(true);
      return;
    }

    if (!isSpeaking && !isListening) {
      setWakeActive(false);
    }
  }, [isConnected, isSpeaking, isListening, micActive]);

  const handleVoiceToggle = useCallback(async () => {
    if (micActive) {
      stopMic();
      setWakeActive(false);
      return;
    }

    try {
      await startAgent();
      setWakeActive(true);
    } catch {
      setWakeActive(false);
    }
  }, [micActive, startAgent, stopMic]);

  const handleOptionSelect = useCallback(
    (optionId: string) => {
      handleSendText(optionId);
    },
    [handleSendText],
  );

  const displayStatus =
    statusText && !statusText.toLowerCase().includes("reconnecting")
      ? statusText
      : undefined;

  return (
    <ConversationPage
      messages={messages}
      isTyping={isSpeaking || (!isVoiceMode && Boolean(displayStatus))}
      statusText={displayStatus}
      connecting={!socketConnected}
      onSendText={handleSendText}
      onVoiceRecorded={() => {}}
      onVoiceToggle={handleVoiceToggle}
      isListening={isListening || isSpeaking}
      voiceLoading={voiceLoading}
      onOptionSelect={handleOptionSelect}
      onConfirm={() => handleOptionSelect("confirm")}
      onModify={() => {}}
      onCancel={() => handleOptionSelect("cancel")}
      onRevert={() => {}}
      onContinueFromHere={() => {}}
      showHeader={showHeader}
      headerSubtitle={sessionTitle ?? "Your AI Business Assistant"}
      fullScreen={fullScreen}
      transparentBg={transparentBg}
      flipCharacter={flipCharacter}
      characterRightOffset={characterRightOffset}
      wakeActive={wakeActive}
      onWakeToggle={handleVoiceToggle}
    />
  );
}

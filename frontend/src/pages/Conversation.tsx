import { useState, useEffect, useRef, useCallback } from "react";

import { ConversationPage, type MessageItem } from "../components/containers";

import { useVoiceAgentStore } from "../lib/voice-agent/store";

import { useEventReceiver } from "../hooks/useEmitReceiver";

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

  const [thinking, setThinking] = useState(false);
  const [wakeActive, setWakeActive] = useState(false);
  const [socketConnected, setSocketConnected] = useState(true);

  const { currentProfile } = useBusinessStore();

  const businessId = currentProfile?.id ?? "";

  const {
    connectionState,
    micActive,
    agentSpeaking,
    statusText: voiceStatusText,
    initAgent,
    startAgent,
    stopMic,
    setStatusText,
  } = useVoiceAgentStore();

  const { events: statusEvents } = useEventReceiver(["agent.progress"]);

  const isConnected =
    connectionState === "ready" ||
    connectionState === "listening" ||
    connectionState === "speaking";

  const isListening = connectionState === "listening";

  const isSpeaking = connectionState === "speaking";

  useEffect(() => {
    const socket = connectSocket();

    const handler = (raw: any) => {
      const msg = typeof raw === "string" ? JSON.parse(raw) : raw;

      const data = msg?.data || {};
      const type = data?.type || "";
      const payload = data?.payload || {};

      if (type === "message" && payload.content) {
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: payload.content,
            type: "text",
            stream: true,
          },
        ]);

        setThinking(false);
        setStatusText("");
      }
    };

    socket.on("message", handler);

    const transcriptHandler = (raw: any) => {
      const msg = typeof raw === "string" ? JSON.parse(raw) : raw;

      const content = msg?.data?.payload?.content || "";

      if (!content) {
        return;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: "user",
          content,
          type: "text",
        },
      ]);

      setThinking(true);
    };

    socket.on("transcript", transcriptHandler);

    const onConnect = () => {
      setSocketConnected(true);
    };

    const onDisconnect = () => {
      setSocketConnected(false);
      setThinking(false);
    };

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);

    setSocketConnected(socket.connected);

    return () => {
      socket.off("message", handler);
      socket.off("transcript", transcriptHandler);
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);

      disconnectSocket();
    };
  }, [setStatusText]);

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

  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  useEffect(() => {
    if (statusEvents.length === 0) {
      return;
    }

    const latest = statusEvents[statusEvents.length - 1];

    const data = latest.data as any;

    const status = data?.payload?.status || "";

    const message = data?.payload?.message || data?.message || "";

    if (
      status === "completed" ||
      status === "failed" ||
      status === "cancelled"
    ) {
      setStatusText("");
      setThinking(false);
      return;
    }

    if (message) {
      setStatusText(message);
    }
  }, [statusEvents, setStatusText]);

  useEffect(() => {
    if (!businessId || !sessionId) {
      return;
    }

    void initAgent(businessId, sessionId);
  }, [businessId, sessionId, initAgent]);

  useEffect(() => {
    const handleVoiceToggleEvent = async () => {
      if (micActive) {
        stopMic();
        setWakeActive(false);
      } else {
        try {
          await startAgent();
          setWakeActive(true);
        } catch {
          setWakeActive(false);
        }
      }

      window.dispatchEvent(
        new CustomEvent("tendo:recording-state", {
          detail: {
            recording: !micActive,
          },
        }),
      );
    };

    window.addEventListener("tendo:voice-toggle", handleVoiceToggleEvent);

    return () => {
      window.removeEventListener("tendo:voice-toggle", handleVoiceToggleEvent);
    };
  }, [micActive, startAgent, stopMic]);

  useEffect(() => {
    if (isConnected && micActive) {
      setWakeActive(true);
      return;
    }

    if (!isSpeaking && !isListening) {
      setWakeActive(false);
    }
  }, [isConnected, isSpeaking, isListening, micActive]);

  const handleSendText = (text: string) => {
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

    setThinking(true);

    sendChatText(text);

    if (onFirstMessage && messages.length === 0) {
      onFirstMessage();
    }
  };

  const pendingMsg = useWorkspaceStore((state) => state.pendingChatMessage);

  const pendingSentRef = useRef<string | null>(null);

  useEffect(() => {
    if (pendingMsg && pendingMsg !== pendingSentRef.current) {
      pendingSentRef.current = pendingMsg;

      handleSendText(pendingMsg);

      useWorkspaceStore.getState().setPendingChatMessage(null);
    }
  }, [pendingMsg]);

  const handleVoiceToggle = async () => {
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
  };

  const handleOptionSelect = (optionId: string) => {
    handleSendText(optionId);
  };

  const findOptionContext = (
    optionId: string,
  ): {
    id: string;
    name: string;
    label: string;
    description?: string;
  } | null => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];

      if (msg.type === "input" && msg.inputSpec?.fields) {
        for (const field of msg.inputSpec.fields) {
          if (field.type === "radio" && field.options) {
            const found = field.options.find(
              (option) => option.id === optionId,
            );

            if (found) {
              return found;
            }
          }
        }
      }
    }

    return null;
  };

  const voiceLoading =
    connectionState === "initializing" ||
    connectionState === "connecting" ||
    connectionState === "waiting_for_agent";

  return (
    <ConversationPage
      messages={messages}
      isTyping={thinking || isSpeaking}
      statusText={
        voiceStatusText && !voiceStatusText.includes("reconnecting")
          ? voiceStatusText
          : undefined
      }
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

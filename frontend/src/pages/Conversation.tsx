import { useState, useEffect, useRef, useCallback } from "react";
import { ConversationPage, type MessageItem } from "../components/containers";
import type { InputSpec } from "../components/containers/ConversationPage";
import { useVoiceStore } from "../store/voice";
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
  const businessId = currentProfile?.id || "";
  const {
    connectionState,
    micActive,
    agentSpeaking,
    statusText: voiceStatusText,
    startAgent,
    stopAgent,
    toggleMic,
    setStatusText,
  } = useVoiceStore();
  const { events: statusEvents } = useEventReceiver(["agent.progress"]);

  const isConnected =
    connectionState === "connected" ||
    connectionState === "listening" ||
    connectionState === "speaking";
  const isListening = connectionState === "listening";
  const isSpeaking = connectionState === "speaking";

  // ---------------------------------------------------------------
  // Chat text via Socket.IO (completely separate from voice)
  // ---------------------------------------------------------------

  useEffect(() => {
    const socket = connectSocket();

    const handler = (raw: any) => {
      const msg = typeof raw === "string" ? JSON.parse(raw) : raw;
      const data = msg.data || {};
      const type = data.type || "";
      const payload = data.payload || {};

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
      if (content) {
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
      }
    };

    socket.on("transcript", transcriptHandler);

    const onConnect = () => setSocketConnected(true);
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
  }, []);

  const sendChatText = useCallback(
    (text: string) => {
      if (!text.trim() || !businessId || !sessionId) return;

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

  // ---------------------------------------------------------------
  // Sync initialMessages when they change (e.g., switching sessions)
  // ---------------------------------------------------------------

  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  // Sync Socket.IO progress events into the voice store
  useEffect(() => {
    if (statusEvents.length > 0) {
      const latest = statusEvents[statusEvents.length - 1];
      const data = latest.data as any;
      const msg = data?.payload?.message || data?.message || "";
      if (msg) setStatusText(msg);
    }
  }, [statusEvents]);

  // ---------------------------------------------------------------
  // Voice agent (LiveKit) — separate from text chat
  // ---------------------------------------------------------------

  useEffect(() => {
    const bizId = currentProfile?.id;
    if (bizId && connectionState === "disconnected") {
      startAgent({ businessId: bizId, sessionId, recordId });
    }
  }, [currentProfile?.id, sessionId]);

  // Listen for external voice toggle events
  useEffect(() => {
    const handleVoiceToggleEvent = async () => {
      if (micActive) {
        await toggleMic();
        setWakeActive(false);
      } else {
        await toggleMic();
        setWakeActive(true);
      }
      window.dispatchEvent(
        new CustomEvent("tendo:recording-state", {
          detail: { recording: !micActive },
        }),
      );
    };
    window.addEventListener("tendo:voice-toggle", handleVoiceToggleEvent);
    return () =>
      window.removeEventListener("tendo:voice-toggle", handleVoiceToggleEvent);
  }, [micActive]);

  useEffect(() => {
    if (isConnected && micActive) {
      setWakeActive(true);
    } else if (!isSpeaking && !isListening) {
      setWakeActive(false);
    }
  }, [isConnected, isSpeaking, isListening, micActive]);

  // ---------------------------------------------------------------
  // Send text handler — sends via socket, not voice
  // ---------------------------------------------------------------

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

    // Send to backend via Socket.IO
    sendChatText(text);

    if (onFirstMessage && messages.length === 0) onFirstMessage();
  };

  const pendingMsg = useWorkspaceStore((s) => s.pendingChatMessage);
  const pendingSentRef = useRef<string | null>(null);

  useEffect(() => {
    if (pendingMsg && pendingMsg !== pendingSentRef.current) {
      pendingSentRef.current = pendingMsg;
      handleSendText(pendingMsg);
      useWorkspaceStore.getState().setPendingChatMessage(null);
    }
  }, [pendingMsg]);

  const handleVoiceToggle = async () => {
    await toggleMic();
    setWakeActive(!micActive);
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
            const found = field.options.find((o) => o.id === optionId);
            if (found) return found;
          }
        }
      }
    }
    return null;
  };

  return (
    <>
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
        voiceLoading={connectionState === "connecting"}
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
        onWakeToggle={async () => {
          await toggleMic();
          setWakeActive(!micActive);
        }}
      />
    </>
  );
}

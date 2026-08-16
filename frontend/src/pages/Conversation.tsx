import { useState, useEffect, useRef } from "react";
import { ConversationPage, type MessageItem } from "../components/containers";
import type { InputSpec } from "../components/containers/ConversationPage";
import { useVoiceStore } from "../store/voice";
import { useEventReceiver } from "../hooks/useEmitReceiver";
import { SpeakingIndicator } from "../components/SpeakingIndicator";
import { useBusinessStore } from "../store/business";
import { useWorkspaceStore } from "../store/workspace";

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
  const { currentProfile } = useBusinessStore();
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
  const { events: statusEvents, clear: clearStatus } = useEventReceiver([
    "progress",
  ]);

  const isConnected =
    connectionState === "connected" ||
    connectionState === "listening" ||
    connectionState === "speaking";
  const isListening = connectionState === "listening";
  const isSpeaking = connectionState === "speaking";

  // Sync initialMessages when they change (e.g., switching sessions)
  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  // Sync Socket.IO progress events into the voice store
  useEffect(() => {
    if (statusEvents.length > 0) {
      const latest = statusEvents[statusEvents.length - 1];
      const msg =
        (latest.payload as any)?.message ||
        (latest.payload as any)?.payload?.message ||
        "";
      if (msg) setStatusText(msg);
    }
  }, [statusEvents]);

  const lastMsgId = useRef("");

  // Voice agent is managed by WorkspaceLayout (start/stop on mount/unmount).
  // This component just uses the already-connected store.
  useEffect(() => {
    // If workspace layout hasn't started the agent yet (e.g., direct navigation),
    // start it here as a fallback.
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

  // When voice connects successfully, mark as active
  useEffect(() => {
    if (isConnected && micActive) {
      setWakeActive(true);
    } else if (!isSpeaking && !isListening) {
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

  const findPendingQuestion = (): string | null => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg.role === "user") break;
      if (msg.type === "input" && msg.inputSpec?.fields) {
        const field = msg.inputSpec.fields[0];
        if (field.type === "text") {
          return field.description || field.name || null;
        }
        if (field.type === "radio") {
          return field.options?.[0]?.name || null;
        }
      }
    }
    return null;
  };

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
      <SpeakingIndicator
        active={isListening || isSpeaking}
        speaking={agentSpeaking}
        statusText={voiceStatusText || undefined}
      />
      <ConversationPage
        messages={messages}
        isTyping={thinking || isSpeaking}
        statusText={voiceStatusText || undefined}
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

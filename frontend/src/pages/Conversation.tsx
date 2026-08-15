import { useState, useEffect, useRef } from "react";
import { ConversationPage, type MessageItem } from "../components/containers";
import type { InputSpec } from "../components/containers/ConversationPage";
import { useVoiceSession } from "../hooks/useVoiceSession";
import { useEventReceiver } from "../hooks/useEmitReceiver";
import { SpeakingIndicator } from "../components/SpeakingIndicator";
import { useBusinessStore } from "../store/business";
import { useWorkspaceStore } from "../store/workspace";
import { resumeSession } from "../lib/services/business";

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
  const voice = useVoiceSession();
  const { events: statusEvents, clear: clearStatus } = useEventReceiver([
    "progress",
  ]);

  // Sync initialMessages when they change (e.g., switching sessions)
  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);
  const connected = useRef(false);
  const lastMsgId = useRef("");
  const currentBusinessId = useRef<string | null>(null);

  useEffect(() => {
    const bizId = currentProfile?.id;
    if (bizId) {
      voice.warmConnect({ sessionId, businessId: bizId });
    }
    return () => {
      voice.disconnect();
    };
  }, [currentProfile?.id, sessionId]);

  useEffect(() => {
    const handleVoiceToggleEvent = async () => {
      if (voice.isListening) {
        voice.disconnect();
        setWakeActive(false);
      } else {
        const bizId = currentProfile?.id;
        if (!bizId) return;
        if (!voice.isConnected) {
          await voice.connect({ sessionId, businessId: bizId });
        }
        await voice.startListening();
        setWakeActive(true);
      }
      window.dispatchEvent(
        new CustomEvent("tendo:recording-state", {
          detail: { recording: !voice.isListening },
        }),
      );
    };
    window.addEventListener("tendo:voice-toggle", handleVoiceToggleEvent);
    return () =>
      window.removeEventListener("tendo:voice-toggle", handleVoiceToggleEvent);
  }, [voice.isListening, voice.isConnected]);

  // When voice connects successfully, mark as active
  useEffect(() => {
    if (voice.isConnected) {
      setWakeActive(true);
    } else if (!voice.isSpeaking && !voice.isListening) {
      setWakeActive(false);
    }
  }, [voice.isConnected, voice.isSpeaking, voice.isListening]);

  // When a voice transcript arrives, show it as a user message and trigger thinking
  const lastTranscriptRef = useRef<string | null>(null);
  useEffect(() => {
    if (!voice.lastTranscript) return;
    if (voice.lastTranscript === lastTranscriptRef.current) return;
    lastTranscriptRef.current = voice.lastTranscript;

    setMessages((prev) => [
      ...prev,
      {
        id: `user-voice-${Date.now()}`,
        role: "user",
        content: voice.lastTranscript!,
        type: "text",
      },
    ]);
    setThinking(true);
  }, [voice.lastTranscript]);

  // Display agent messages when they arrive
  useEffect(() => {
    if (!voice.lastMessage) return;
    if (voice.lastMessage.id === lastMsgId.current) return;
    lastMsgId.current = voice.lastMessage.id;
    setThinking(false);
    clearStatus();

    console.log("[Conversation] lastMessage:", voice.lastMessage);

    const { response, msgType, questions } = voice.lastMessage;

    // Add the text response as a message bubble
    if (response) {
      setMessages((prev) => [
        ...prev,
        {
          id: `text-${voice.lastMessage!.id}`,
          role: "assistant",
          content: response,
          type: "text",
        },
      ]);
    }

    // If type is "question", add the input card below the text
    if (msgType === "question" && questions) {
      setMessages((prev) => [
        ...prev,
        {
          id: `input-${voice.lastMessage!.id}`,
          role: "assistant",
          content: "",
          type: "input",
          inputSpec: questions as InputSpec,
        },
      ]);
    }
  }, [voice.lastMessage]);

  useEffect(() => {
    if (voice.errorMessage) {
      console.warn("[Voice] error:", voice.errorMessage);
    }
  }, [voice.errorMessage]);

  const handleSendText = (text: string) => {
    // Find option context if this was a radio select
    const optionContext = findOptionContext(text);
    const displayText = optionContext?.label || text;

    let sendText: string;
    if (optionContext) {
      sendText = `label: ${optionContext.label}, answer: ${optionContext.id}, description: ${optionContext.description || ""}`;
    } else {
      // Check if there's a pending question — format as reply to that question
      const pendingQuestion = findPendingQuestion();
      if (pendingQuestion) {
        sendText = `${pendingQuestion}: ${text}`;
      } else {
        sendText = text;
      }
    }

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
    const scope = recordId ? "record" : undefined;
    voice.sendText(
      sendText,
      undefined,
      currentProfile?.id,
      recordId,
      sessionId,
    );
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
    if (voice.isListening || voice.isSpeaking) {
      voice.stopListening();
      setWakeActive(false);
    } else {
      const bizId = currentProfile?.id;
      if (!bizId) {
        return;
      }
      await voice.connect({ sessionId, businessId: bizId });
      setWakeActive(true);
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
        active={voice.state === "listening" || voice.state === "speaking"}
        speaking={voice.agentSpeaking}
        statusText={
          statusEvents.length > 0
            ? (statusEvents[statusEvents.length - 1].data as any)?.message
            : undefined
        }
      />
      <ConversationPage
        messages={messages}
        isTyping={thinking || voice.isSpeaking}
        statusText={
          statusEvents.length > 0
            ? (statusEvents[statusEvents.length - 1].data as any)?.message
            : undefined
        }
        onSendText={handleSendText}
        onVoiceRecorded={() => {}}
        onVoiceToggle={handleVoiceToggle}
        isListening={voice.isListening || voice.isSpeaking}
        voiceLoading={voice.state === "connecting" || voice.state === "warming"}
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
          if (wakeActive) {
            voice.disconnect();
            setWakeActive(false);
          } else {
            const bizId = currentProfile?.id;
            if (!bizId) return;
            await voice.connect({ sessionId, businessId: bizId });
            await voice.startListening();
            setWakeActive(true);
          }
        }}
      />
    </>
  );
}

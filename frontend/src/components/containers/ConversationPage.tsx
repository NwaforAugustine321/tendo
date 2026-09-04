import { useRef, useEffect, useState } from "react";

import {
  MessageBubble,
  UnderstandingCard,
  InputCard,
  ConfirmationCard,
  OperationCard,
  TextInput,
  EmptyState,
} from "../atoms";

import { useAgentSessionStatus } from "../../hooks/useAgentSessionStatus";
import { useVoiceAgentStore } from "../../lib/voice-agent/store";

const BOTTOM_FOLLOW_THRESHOLD = 80;

function isNearBottom(el: HTMLElement) {
  return (
    el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_FOLLOW_THRESHOLD
  );
}

export type InputSpec = {
  fields: Array<{
    id?: string;
    name: string;
    label?: string;
    placeholder?: string;
    description?: string;
  }>;
};

export type MessageItem = {
  id: string;
  role: "user" | "assistant";
  content: string;
  type:
    | "text"
    | "understanding"
    | "options"
    | "confirmation"
    | "operation"
    | "input";
  audioUrl?: string;
  stream?: boolean;
  understanding?: {
    title?: string;
    businessName?: string;
    activities?: string[];
    behaviors?: string[];
    note?: string;
  };
  options?: {
    prompt: string;
    choices: {
      id: string;
      label: string;
      recommended?: boolean;
    }[];
  };
  confirmation?: {
    summary: string;
    details: {
      label: string;
      value: string;
    }[];
  };
  operation?: {
    operationType: string;
    changes: {
      label: string;
      before: string;
      after: string;
    }[];
  };
  inputSpec?: InputSpec;
};

type Props = {
  messages: MessageItem[];
  isTyping: boolean;
  connecting?: boolean;
  onSendText: (text: string) => void;
  onVoiceRecorded: (blob: Blob) => void;
  onVoiceToggle?: () => void;
  isListening?: boolean;
  voiceLoading?: boolean;
  onOptionSelect: (optionId: string) => void;
  onConfirm?: () => void;
  onModify?: () => void;
  onCancel?: () => void;
  onRevert?: (messageId: string) => void;
  onContinueFromHere?: (messageId: string) => void;
  showHeader?: boolean;
  headerTitle?: string;
  headerSubtitle?: string;
  fullScreen?: boolean;
  transparentBg?: boolean;
  onWakeToggle?: () => void;
  wakeActive?: boolean;
};

type InteractionMode = "text" | "voice";

function getPresenceText(event: {
  event: string;
  data: Record<string, unknown>;
}): string {
  const data = event.data;

  if (data?.type !== "voice.presence" && data?.type !== "text.presence") {
    return "";
  }

  const payload = data.payload;

  if (!payload || typeof payload !== "object") {
    return "";
  }

  const message = (payload as Record<string, unknown>).message;

  return typeof message === "string" ? message.trim() : "";
}

export function ConversationPage({
  messages,
  isTyping,
  connecting = false,
  onSendText,
  onVoiceRecorded,
  onVoiceToggle,
  isListening = false,
  voiceLoading = false,
  onConfirm,
  onModify,
  onCancel,
  onRevert,
  onContinueFromHere,
  fullScreen = true,
  transparentBg = false,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const followBottomRef = useRef(true);

  const { events: presenceEvents, clear: clearPresence } =
    useAgentSessionStatus(["voice.presence", "text.presence"]);

  const micActive = useVoiceAgentStore((state) => state.micActive);

  const agentSpeaking = useVoiceAgentStore((state) => state.agentSpeaking);

  const [interactionMode, setInteractionMode] = useState<InteractionMode>(
    micActive ? "voice" : "text",
  );

  const [textRequestActive, setTextRequestActive] = useState(false);

  const wasTypingRef = useRef(isTyping);
  const wasMicActiveRef = useRef(micActive);

  /*
   * Always use the newest presence event.
   *
   * Do not accumulate older presence messages.
   */
  let latestPresence = "";

  for (let index = presenceEvents.length - 1; index >= 0; index -= 1) {
    const text = getPresenceText(presenceEvents[index]);

    if (text) {
      latestPresence = text;
      break;
    }
  }

  /*
   * Clear the active text interaction when the response
   * finishes.
   */
  useEffect(() => {
    if (wasTypingRef.current && !isTyping) {
      setTextRequestActive(false);
      clearPresence();
    }

    wasTypingRef.current = isTyping;
  }, [isTyping, clearPresence]);

  /*
   * Voice lifecycle.
   *
   * Starting voice clears previous text state.
   * Stopping voice returns the interaction to text mode.
   */
  useEffect(() => {
    const wasMicActive = wasMicActiveRef.current;

    if (!wasMicActive && micActive) {
      setTextRequestActive(false);
      clearPresence();
      setInteractionMode("voice");
    }

    if (wasMicActive && !micActive) {
      setTextRequestActive(false);
      clearPresence();
      setInteractionMode("text");
    }

    wasMicActiveRef.current = micActive;
  }, [micActive, clearPresence]);

  /*
   * Sending text always switches the current interaction
   * to text, even if the LiveKit voice connection remains active.
   */
  const handleSendText = (text: string) => {
    clearPresence();

    setInteractionMode("text");
    setTextRequestActive(true);

    onSendText(text);
  };

  /*
   * Voice button changes the current interaction mode.
   */
  const handleVoiceToggle = () => {
    clearPresence();
    setTextRequestActive(false);

    if (micActive) {
      setInteractionMode("text");
    } else {
      setInteractionMode("voice");
    }

    onVoiceToggle?.();
  };

  /*
   * Indicator priority:
   *
   * 1. Agent speaking
   * 2. Latest presence
   * 3. Voice listening
   * 4. Text reasoning
   * 5. Nothing
   *
   * This intentionally does NOT depend on interactionMode.
   * A connected/active microphone should still show
   * Listening... even if the last interaction was text.
   */
  let displayedStatus = "";

  if (agentSpeaking) {
    displayedStatus = "Speaking...";
  } else if (latestPresence) {
    displayedStatus = latestPresence;
  } else if (micActive) {
    displayedStatus = "Listening...";
  } else if (textRequestActive) {
    displayedStatus = "Reasoning...";
  }

  useEffect(() => {
    const el = scrollRef.current;

    if (!el) return;

    const handleScroll = () => {
      followBottomRef.current = isNearBottom(el);
    };

    el.addEventListener("scroll", handleScroll, {
      passive: true,
    });

    return () => {
      el.removeEventListener("scroll", handleScroll);
    };
  }, []);

  useEffect(() => {
    const el = scrollRef.current;

    if (!el) return;

    const observer = new ResizeObserver(() => {
      if (!followBottomRef.current) return;

      el.scrollTo({
        top: el.scrollHeight,
      });
    });

    if (el.firstElementChild) {
      observer.observe(el.firstElementChild);
    }

    return () => observer.disconnect();
  }, [messages.length]);

  useEffect(() => {
    const el = scrollRef.current;

    if (!el) return;

    const sentByUser = messages[messages.length - 1]?.role === "user";

    if (sentByUser) {
      followBottomRef.current = true;
    } else if (!followBottomRef.current) {
      return;
    }

    el.scrollTo({
      top: el.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isTyping]);

  return (
    <div
      className={`relative flex flex-col overflow-hidden bg-[#0a0a0a] ${
        fullScreen ? "h-dvh" : "h-full"
      }`}
    >
      <div
        ref={scrollRef}
        className="relative z-10 flex-1 overflow-y-auto px-3 pb-4 pt-4 sm:px-5"
      >
        {messages.length === 0 && !isTyping ? (
          <EmptyState />
        ) : (
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.map((msg, idx) => {
              if (msg.type === "understanding" && msg.understanding) {
                return (
                  <UnderstandingCard
                    key={msg.id}
                    title={msg.understanding.title}
                    businessName={msg.understanding.businessName}
                    activities={msg.understanding.activities}
                    behaviors={msg.understanding.behaviors}
                    note={msg.understanding.note}
                  />
                );
              }

              if (msg.type === "input" && msg.inputSpec) {
                const isLast = idx === messages.length - 1;

                return (
                  <InputCard
                    key={msg.id}
                    fields={(msg.inputSpec.fields as any[]) || []}
                    onSubmit={isLast ? handleSendText : () => {}}
                    disabled={!isLast}
                  />
                );
              }

              if (msg.type === "confirmation" && msg.confirmation) {
                return (
                  <ConfirmationCard
                    key={msg.id}
                    summary={msg.confirmation.summary}
                    details={msg.confirmation.details}
                    onConfirm={onConfirm ?? (() => {})}
                    onModify={onModify ?? (() => {})}
                    onCancel={onCancel ?? (() => {})}
                  />
                );
              }

              if (msg.type === "operation" && msg.operation) {
                return (
                  <OperationCard
                    key={msg.id}
                    operationType={msg.operation.operationType}
                    changes={msg.operation.changes}
                    onRevert={onRevert ? () => onRevert(msg.id) : undefined}
                    onContinueFromHere={
                      onContinueFromHere
                        ? () => onContinueFromHere(msg.id)
                        : undefined
                    }
                  />
                );
              }

              return (
                <MessageBubble
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  audioUrl={msg.audioUrl}
                  stream={
                    msg.stream === true &&
                    msg.role === "assistant" &&
                    idx === messages.length - 1
                  }
                />
              );
            })}

            {displayedStatus && (
              <div className="inline-flex w-fit items-center gap-2 rounded-2xl border border-zinc-800/90 bg-[#141414] px-4 py-2.5">
                <span className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
                </span>

                <span className="animate-pulse text-xs text-zinc-400">
                  {displayedStatus}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <div
        className={`relative z-10 border-t border-zinc-800/40 ${
          transparentBg ? "bg-transparent" : "bg-[#0a0a0a]"
        } px-3 py-3 sm:px-5`}
      >
        <div className="mx-auto max-w-2xl">
          {connecting && (
            <div className="mb-2 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[11px] text-zinc-400">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
              Connecting...
            </div>
          )}

          <div className="mb-2">
            <TextInput
              onSend={handleSendText}
              onVoiceRecorded={onVoiceRecorded}
              onVoiceToggle={onVoiceToggle ? handleVoiceToggle : undefined}
              isListening={isListening}
              voiceLoading={voiceLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

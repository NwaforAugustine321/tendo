import { useRef, useEffect, useState } from "react";
import {
  MessageBubble,
  UnderstandingCard,
  InputCard,
  ConfirmationCard,
  OperationCard,
  TextInput,
  VoiceButton,
  EmptyState,
} from "../atoms";
import { TalkingCharacter } from "./TalkingCharacter";

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
  understanding?: {
    title?: string;
    businessName?: string;
    activities?: string[];
    behaviors?: string[];
    note?: string;
  };
  options?: {
    prompt: string;
    choices: { id: string; label: string; recommended?: boolean }[];
  };
  confirmation?: {
    summary: string;
    details: { label: string; value: string }[];
  };
  operation?: {
    operationType: string;
    changes: { label: string; before: string; after: string }[];
  };
  inputSpec?: InputSpec;
};

type Props = {
  messages: MessageItem[];
  isTyping: boolean;
  statusText?: string;
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
  flipCharacter?: boolean;
  characterRightOffset?: number;
  onWakeToggle?: () => void;
  wakeActive?: boolean;
};

export function ConversationPage({
  messages,
  isTyping,
  statusText,
  connecting = false,
  onSendText,
  onVoiceRecorded,
  onVoiceToggle,
  isListening = false,
  voiceLoading = false,
  onOptionSelect,
  onConfirm,
  onModify,
  onCancel,
  onRevert,
  onContinueFromHere,
  showHeader = true,
  headerTitle = "Tendo",
  headerSubtitle = "Your AI Business Assistant",
  fullScreen = true,
  transparentBg = false,
  flipCharacter = false,
  characterRightOffset = 0,
  onWakeToggle,
  wakeActive = false,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [displayedStatus, setDisplayedStatus] = useState("");
  const streamRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (streamRef.current) clearInterval(streamRef.current);
    if (!statusText) {
      setDisplayedStatus("");
      return;
    }
    setDisplayedStatus("");
    let i = 0;
    streamRef.current = setInterval(() => {
      i++;
      if (i >= statusText.length) {
        setDisplayedStatus(statusText);
        if (streamRef.current) clearInterval(streamRef.current);
      } else {
        setDisplayedStatus(statusText.slice(0, i));
      }
    }, 20);
    return () => {
      if (streamRef.current) clearInterval(streamRef.current);
    };
  }, [statusText]);

  useEffect(() => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const observer = new ResizeObserver(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    });
    // Observe the inner content wrapper so that streaming text
    // (which grows the element height) triggers auto-scroll.
    if (el.firstElementChild) observer.observe(el.firstElementChild);
    return () => observer.disconnect();
  }, [messages.length]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isTyping]);

  return (
    <div
      className={`relative flex flex-col overflow-hidden bg-[#0a0a0a] ${fullScreen ? "h-dvh" : "h-full"}`}
    >
      {/* {showHeader && (
        <header className="relative z-10 flex flex-col items-center pt-4 pb-2 mb-4">
          <h1 className="text-lg font-bold tracking-[-0.03em] text-white">{headerTitle}</h1>
          <p className="mt-0.5 text-xs text-zinc-400">{headerSubtitle}</p>
        </header>
      )} */}

      <div
        ref={scrollRef}
        className="relative z-10 flex-1 overflow-y-auto px-3 pt-4 pb-4 sm:px-5"
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
                    onSubmit={isLast ? onSendText : () => {}}
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
            {isTyping && (
              <div className="inline-flex w-fit items-center gap-2 rounded-2xl border border-zinc-800/90 bg-[#141414] px-4 py-2.5">
                <span className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
                </span>
                {displayedStatus && (
                  <span className="text-xs text-zinc-400">
                    {displayedStatus}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div
        className={`relative z-10 border-t border-zinc-800/40 ${transparentBg ? "bg-transparent" : "bg-[#0a0a0a]"} px-3 py-3 sm:px-5`}
      >
        <div className="mx-auto max-w-2xl">
          {connecting && (
            <div className="mb-2 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[11px] text-zinc-400">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
              Connecting...
            </div>
          )}
          <div className="mb-2 flex items-center gap-2">
            <VoiceButton
              onRecorded={onVoiceRecorded}
              onToggle={onVoiceToggle}
              isListening={isListening}
              loading={voiceLoading}
            />
            <TextInput onSend={onSendText} />
          </div>
        </div>
      </div>

      {fullScreen && (
        <TalkingCharacter
          isSpeaking={isTyping}
          flipX={flipCharacter}
          rightOffset={characterRightOffset}
        />
      )}
    </div>
  );
}

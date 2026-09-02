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

import { TalkingCharacter } from "./TalkingCharacter";

/**
 * How far from the bottom still counts as "following the conversation".
 */
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

  /**
   * Whether the view is following the bottom of the conversation.
   *
   * Once the user scrolls up, auto-scroll stops until they come back down.
   */
  const followBottomRef = useRef(true);

  const [displayedStatus, setDisplayedStatus] = useState("");

  useEffect(() => {
    setDisplayedStatus(statusText || "");
  }, [statusText]);

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
      /**
       * Reading back while streaming must not be interrupted.
       */
      if (!followBottomRef.current) return;

      /**
       * Instant, because streamed text resizes the wrapper every few ms
       * and queued smooth animations never settle.
       */
      el.scrollTo({
        top: el.scrollHeight,
      });
    });

    /**
     * Observe the inner content wrapper so that streaming text
     * (which grows the element height) triggers auto-scroll.
     */
    if (el.firstElementChild) {
      observer.observe(el.firstElementChild);
    }

    return () => observer.disconnect();
  }, [messages.length]);

  useEffect(() => {
    const el = scrollRef.current;

    if (!el) return;

    /**
     * Sending a message always returns the view to the bottom.
     */
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
      {/*
      {showHeader && (
        <header className="relative z-10 mb-4 flex flex-col items-center pb-2 pt-4">
          <h1 className="text-lg font-bold tracking-[-0.03em] text-white">
            {headerTitle}
          </h1>

          <p className="mt-0.5 text-xs text-zinc-400">
            {headerSubtitle}
          </p>
        </header>
      )}
      */}

      {/* Conversation */}
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
                  <span
                    key={displayedStatus}
                    className="animate-bounce text-xs text-zinc-400"
                  >
                    {displayedStatus}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
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

          {/* Mic + text + send are now inside ONE input container */}
          <div className="mb-2">
            <TextInput
              onSend={onSendText}
              onVoiceRecorded={onVoiceRecorded}
              onVoiceToggle={onVoiceToggle}
              isListening={isListening}
              voiceLoading={voiceLoading}
            />
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

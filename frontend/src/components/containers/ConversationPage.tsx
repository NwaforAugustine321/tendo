import { useEffect, useRef } from "react";

import {
  MessageBubble,
  UnderstandingCard,
  InputCard,
  ConfirmationCard,
  OperationCard,
  EmptyState,
} from "../atoms";

const BOTTOM_FOLLOW_THRESHOLD = 80;

function isNearBottom(element: HTMLElement): boolean {
  return (
    element.scrollHeight - element.scrollTop - element.clientHeight <=
    BOTTOM_FOLLOW_THRESHOLD
  );
}

export type InputField = {
  id?: string;
  name: string;
  label?: string;
  placeholder?: string;
  description?: string;
  type?: string;
  options?: {
    id: string;
    label: string;
    description?: string;
  }[];
};

export type InputSpec = {
  fields: InputField[];
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

  /*
   * Whether Tendo is currently processing
   * or speaking.
   */
  isTyping: boolean;

  /*
   * Current runtime status text.
   *
   * Examples:
   *   "Reasoning..."
   *   "Understanding your business..."
   *   "Checking your data..."
   *   "Speaking..."
   *
   * The component must never hard-code
   * a reasoning message.
   */
  statusText?: string;

  fullScreen?: boolean;
  transparentBg?: boolean;

  onOptionSelect: (optionId: string) => void;

  onConfirm?: () => void;
  onModify?: () => void;
  onCancel?: () => void;

  onRevert?: (messageId: string) => void;

  onContinueFromHere?: (messageId: string) => void;

  onSendText?: (text: string) => void;
};

export function ConversationPage({
  messages,
  isTyping,
  statusText,
  fullScreen = true,
  transparentBg = false,
  onSendText,
  onConfirm,
  onModify,
  onCancel,
  onRevert,
  onContinueFromHere,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const contentRef = useRef<HTMLDivElement>(null);

  const followBottomRef = useRef(true);

  const mountedRef = useRef(false);

  /*
   * Scroll tracking.
   */
  useEffect(() => {
    const element = scrollRef.current;

    if (!element) {
      return;
    }

    const handleScroll = () => {
      followBottomRef.current = isNearBottom(element);
    };

    element.addEventListener("scroll", handleScroll, {
      passive: true,
    });

    followBottomRef.current = true;

    return () => {
      element.removeEventListener("scroll", handleScroll);
    };
  }, []);

  /*
   * Observe content size changes.
   *
   * This keeps the conversation pinned
   * while streamed text or status content
   * changes its height.
   */
  useEffect(() => {
    const element = scrollRef.current;

    const content = contentRef.current;

    if (!element || !content) {
      return;
    }

    const scrollToBottom = () => {
      if (!followBottomRef.current) {
        return;
      }

      element.scrollTop = element.scrollHeight;
    };

    const observer = new ResizeObserver(scrollToBottom);

    observer.observe(content);

    return () => {
      observer.disconnect();
    };
  }, []);

  /*
   * Scroll when messages or typing/status
   * state changes.
   */
  useEffect(() => {
    const element = scrollRef.current;

    if (!element) {
      return;
    }

    const lastMessage = messages[messages.length - 1];

    /*
     * A newly submitted user message
     * should always move to the bottom.
     */
    if (lastMessage?.role === "user") {
      followBottomRef.current = true;
    }

    if (!followBottomRef.current) {
      return;
    }

    const frame = requestAnimationFrame(() => {
      element.scrollTo({
        top: element.scrollHeight,
        behavior: mountedRef.current ? "smooth" : "auto",
      });

      mountedRef.current = true;
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [messages, isTyping, statusText]);

  const hasMessages = messages.length > 0;

  /*
   * Only show the empty state when
   * there is no conversation AND Tendo
   * is not doing anything.
   */
  const showEmptyState = !hasMessages && !isTyping;

  /*
   * Show the runtime indicator when
   * Tendo is processing.
   *
   * statusText is optional, so this
   * component does not invent a status.
   */
  const showStatus = isTyping && Boolean(statusText);

  return (
    <div
      className={[
        "relative flex min-h-0 flex-col overflow-hidden",
        fullScreen ? "h-dvh" : "h-full",
        transparentBg ? "bg-transparent" : "bg-[#0a0a0a]",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div
        ref={scrollRef}
        className="
          relative z-10
          min-h-0 flex-1
          overflow-y-auto
          overscroll-contain
          px-3 pb-4 pt-4
          sm:px-5
        "
      >
        {showEmptyState ? (
          <EmptyState />
        ) : (
          <div
            ref={contentRef}
            className="
              mx-auto
              flex
              max-w-2xl
              flex-col
              space-y-4
            "
          >
            {messages.map((message, index) => {
              const isLast = index === messages.length - 1;

              /*
               * Understanding
               */
              if (message.type === "understanding" && message.understanding) {
                return (
                  <UnderstandingCard
                    key={message.id}
                    title={message.understanding.title}
                    businessName={message.understanding.businessName}
                    activities={message.understanding.activities}
                    behaviors={message.understanding.behaviors}
                    note={message.understanding.note}
                  />
                );
              }

              /*
               * Input
               */
              if (message.type === "input" && message.inputSpec) {
                return (
                  <InputCard
                    key={message.id}
                    fields={message.inputSpec.fields}
                    onSubmit={isLast ? (onSendText ?? (() => {})) : () => {}}
                    disabled={!isLast}
                  />
                );
              }

              /*
               * Confirmation
               */
              if (message.type === "confirmation" && message.confirmation) {
                return (
                  <ConfirmationCard
                    key={message.id}
                    summary={message.confirmation.summary}
                    details={message.confirmation.details}
                    onConfirm={onConfirm ?? (() => {})}
                    onModify={onModify ?? (() => {})}
                    onCancel={onCancel ?? (() => {})}
                  />
                );
              }

              /*
               * Operation
               */
              if (message.type === "operation" && message.operation) {
                return (
                  <OperationCard
                    key={message.id}
                    operationType={message.operation.operationType}
                    changes={message.operation.changes}
                    onRevert={onRevert ? () => onRevert(message.id) : undefined}
                    onContinueFromHere={
                      onContinueFromHere
                        ? () => onContinueFromHere(message.id)
                        : undefined
                    }
                  />
                );
              }

              /*
               * Regular text message.
               */
              return (
                <MessageBubble
                  key={message.id}
                  role={message.role}
                  content={message.content}
                  audioUrl={message.audioUrl}
                  stream={
                    message.stream === true &&
                    message.role === "assistant" &&
                    isLast
                  }
                />
              );
            })}

            {showStatus && (
              <div
                className="
                  flex
                  items-center
                  gap-2
                  px-2
                  py-2
                  text-xs
                  text-zinc-500
                "
              >
                <span
                  className="
                    h-1.5 w-1.5
                    animate-pulse
                    rounded-full
                    bg-zinc-500
                  "
                />

                <span>{statusText}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

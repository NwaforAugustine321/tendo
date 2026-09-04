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
  const followBottomRef = useRef(true);

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
                    onSubmit={isLast ? (onSendText ?? (() => {})) : () => {}}
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
          </div>
        )}
      </div>
    </div>
  );
}

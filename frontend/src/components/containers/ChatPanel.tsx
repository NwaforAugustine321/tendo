import { useCallback, useEffect, useRef, useState } from "react";

import { Plus, History, X, Loader2 } from "lucide-react";

import { Conversation } from "../../pages/Conversation";

import { useBusinessStore } from "../../store/business";
import { useWorkspaceStore } from "../../store/workspace";

import {
  listSessions,
  createSession,
  getSessionMessages,
  deleteSession,
  type ChatSession,
} from "../../lib/services/conversations";

import type { MessageItem } from "./ConversationPage";

type Props = {
  recordId?: string;
};

const PAGE_SIZE = 20;

function mapMessages(
  messages: Array<{
    role: string;
    content: string;
  }>,
  offset: number,
): MessageItem[] {
  return messages.map((message, index) => ({
    id: `msg-${offset + index}`,
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    type: "text",
  }));
}

export function ChatPanel({ recordId }: Props) {
  const { currentProfile } = useBusinessStore();

  const businessId = currentProfile?.id ?? "";

  const pendingMsg = useWorkspaceStore((state) => state.pendingChatMessage);

  const [sessions, setSessions] = useState<ChatSession[]>([]);

  const [activeSessionId, setActiveSessionId] = useState("");

  const [initialMessages, setInitialMessages] = useState<MessageItem[]>([]);

  const [showHistory, setShowHistory] = useState(false);

  const [collapsed, setCollapsed] = useState(false);

  const [loading, setLoading] = useState(true);

  const [loadingMessages, setLoadingMessages] = useState(false);

  const [creatingSession, setCreatingSession] = useState(false);

  /*
   * Every async session/message operation
   * receives a request generation.
   *
   * Older requests are ignored when a newer
   * request has started.
   */
  const requestIdRef = useRef(0);

  /*
   * Prevent duplicate automatic session
   * creation for the same pending message.
   */
  const pendingSessionRef = useRef<string | null>(null);

  /*
   * Load all persisted messages for a session.
   */
  const loadMessagesForSession = useCallback(
    async (sessionId: string, requestId: number) => {
      if (!sessionId || !businessId) {
        return;
      }

      setLoadingMessages(true);
      setInitialMessages([]);

      let offset = 0;

      const allMessages: MessageItem[] = [];

      try {
        while (true) {
          const batch = await getSessionMessages(
            sessionId,
            businessId,
            PAGE_SIZE,
            offset,
          );

          /*
           * User switched session while
           * this request was running.
           */
          if (requestId !== requestIdRef.current) {
            return;
          }

          if (batch.length === 0) {
            break;
          }

          allMessages.push(...mapMessages(batch, offset));

          if (batch.length < PAGE_SIZE) {
            break;
          }

          offset += PAGE_SIZE;
        }

        if (requestId === requestIdRef.current) {
          setInitialMessages(allMessages);
        }
      } catch {
        if (requestId === requestIdRef.current) {
          setInitialMessages([]);
        }
      } finally {
        if (requestId === requestIdRef.current) {
          setLoadingMessages(false);
        }
      }
    },
    [businessId],
  );

  /*
   * Load the sessions for the current
   * business/record.
   *
   * IMPORTANT:
   * pendingMsg is intentionally NOT a
   * dependency here.
   *
   * Pending-message session creation is
   * handled by the separate effect below.
   */
  useEffect(() => {
    if (!businessId) {
      setSessions([]);
      setActiveSessionId("");
      setInitialMessages([]);
      setLoading(false);
      setLoadingMessages(false);
      return;
    }

    const requestId = ++requestIdRef.current;

    let cancelled = false;

    setLoading(true);
    setLoadingMessages(false);
    setSessions([]);
    setActiveSessionId("");
    setInitialMessages([]);

    const load = async () => {
      try {
        const data = await listSessions(businessId, recordId);

        if (cancelled || requestId !== requestIdRef.current) {
          return;
        }

        /*
         * Existing session.
         *
         * The first session returned by
         * the service is treated as the
         * most recent session, matching
         * the existing behavior.
         */
        if (data.length > 0) {
          const session = data[0];

          setSessions(data);
          setActiveSessionId(session.id);

          await loadMessagesForSession(session.id, requestId);

          return;
        }

        /*
         * No existing session.
         *
         * Do NOT create one here.
         *
         * If there is a pending message,
         * the dedicated pending-message
         * effect below will create it.
         */
        setSessions([]);
        setActiveSessionId("");
        setInitialMessages([]);
      } catch {
        if (cancelled || requestId !== requestIdRef.current) {
          return;
        }

        setSessions([]);
        setActiveSessionId("");
        setInitialMessages([]);
      } finally {
        if (!cancelled && requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [businessId, recordId, loadMessagesForSession]);

  /*
   * Select a session.
   */
  const handleSelectSession = useCallback(
    (sessionId: string) => {
      if (!sessionId) {
        return;
      }

      if (sessionId === activeSessionId) {
        setShowHistory(false);
        return;
      }

      /*
       * Invalidate all previous
       * message requests immediately.
       */
      const requestId = ++requestIdRef.current;

      setActiveSessionId(sessionId);

      setInitialMessages([]);
      setLoadingMessages(true);
      setShowHistory(false);

      void loadMessagesForSession(sessionId, requestId);
    },
    [activeSessionId, loadMessagesForSession],
  );

  /*
   * Create a new conversation.
   */
  const handleNewSession = useCallback(async () => {
    if (!businessId || creatingSession) {
      return;
    }

    const requestId = ++requestIdRef.current;

    setCreatingSession(true);

    try {
      const session = await createSession(businessId, "New Session", recordId);

      if (requestId !== requestIdRef.current) {
        return;
      }

      setSessions((previous) => [session, ...previous]);

      setActiveSessionId(session.id);

      setInitialMessages([]);
      setLoadingMessages(false);
      setShowHistory(false);

      /*
       * The pending message, if any,
       * belongs to this newly created
       * session.
       */
      pendingSessionRef.current = pendingMsg ?? null;
    } catch {
      /*
       * HTTP service handles
       * the underlying error.
       */
    } finally {
      if (requestId === requestIdRef.current) {
        setCreatingSession(false);
      }
    }
  }, [businessId, creatingSession, recordId, pendingMsg]);

  /*
   * Handle a pending message when no
   * session exists.
   *
   * This is the ONLY automatic session
   * creation path.
   */
  useEffect(() => {
    if (
      !pendingMsg ||
      !businessId ||
      loading ||
      creatingSession ||
      activeSessionId
    ) {
      return;
    }

    if (pendingSessionRef.current === pendingMsg) {
      return;
    }

    pendingSessionRef.current = pendingMsg;

    const requestId = ++requestIdRef.current;

    setCreatingSession(true);

    createSession(businessId, "New Session", recordId)
      .then((session) => {
        if (requestId !== requestIdRef.current) {
          return;
        }

        setSessions((previous) => [session, ...previous]);

        setActiveSessionId(session.id);

        setInitialMessages([]);
        setLoadingMessages(false);
      })
      .catch(() => {
        if (requestId === requestIdRef.current) {
          pendingSessionRef.current = null;
        }
      })
      .finally(() => {
        if (requestId === requestIdRef.current) {
          setCreatingSession(false);
        }
      });
  }, [
    pendingMsg,
    businessId,
    loading,
    creatingSession,
    activeSessionId,
    recordId,
  ]);

  /*
   * Delete a session.
   */
  const handleCloseSession = useCallback(
    async (sessionId: string) => {
      if (!sessionId || !businessId) {
        return;
      }

      const wasActive = sessionId === activeSessionId;

      /*
       * Remove the session and, if it was
       * active, select the next available
       * session in ONE state update.
       */
      setSessions((previous) => {
        const next = previous.filter((session) => session.id !== sessionId);

        if (wasActive) {
          setActiveSessionId(next[0]?.id ?? "");

          setInitialMessages([]);

          setLoadingMessages(false);
        }

        return next;
      });

      /*
       * Invalidate any message request
       * belonging to the deleted session.
       */
      ++requestIdRef.current;

      try {
        await deleteSession(sessionId, businessId);
      } catch {
        /*
         * HTTP service handles
         * the underlying error.
         */
      }
    },
    [activeSessionId, businessId],
  );

  /*
   * Collapsed chat panel.
   */
  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="
          flex h-full w-10
          items-center justify-center
          border-l border-zinc-800/60
          bg-[#0f0f0f]
          text-zinc-400
          hover:text-zinc-300
        "
        title="Open chat"
      >
        <span
          className="
            rotate-90
            whitespace-nowrap
            text-[10px]
            font-medium
            tracking-wide
          "
        >
          Chat
        </span>
      </button>
    );
  }

  return (
    <div className="flex h-full flex-col bg-[#0f0f0f]">
      {/* Session tabs */}
      <div
        className="
          flex min-h-[36px]
          items-center gap-0.5
          overflow-x-auto
          border-b border-zinc-800/60
          bg-[#0a0a0a]
          px-1
        "
      >
        {sessions.slice(0, 5).map((session) => (
          <div
            key={session.id}
            onClick={() => handleSelectSession(session.id)}
            className={[
              "flex cursor-pointer",
              "items-center gap-1",
              "rounded-t-md px-2.5 py-1.5",
              "text-[11px]",
              "transition-colors",
              activeSessionId === session.id
                ? [
                    "border border-zinc-800/60",
                    "border-b-transparent",
                    "bg-[#0f0f0f]",
                    "text-zinc-200",
                  ].join(" ")
                : ["text-zinc-400", "hover:text-zinc-300"].join(" "),
            ].join(" ")}
          >
            <span className="max-w-[100px] truncate">{session.title}</span>

            <button
              onClick={(event) => {
                event.stopPropagation();

                void handleCloseSession(session.id);
              }}
              className="
                  ml-0.5 rounded p-0.5
                  text-zinc-400
                  hover:bg-zinc-800
                  hover:text-zinc-300
                "
              title="Close session"
            >
              <X size={10} />
            </button>
          </div>
        ))}

        <button
          onClick={() => void handleNewSession()}
          disabled={creatingSession}
          className="
            flex items-center gap-1
            px-2 py-1.5
            text-[11px]
            text-zinc-400
            transition-colors
            hover:text-zinc-300
            disabled:cursor-not-allowed
            disabled:opacity-60
          "
          title="New session"
        >
          New
          {creatingSession ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Plus size={12} />
          )}
        </button>

        <div className="flex-1" />

        <button
          onClick={() => setShowHistory((previous) => !previous)}
          className={[
            "rounded p-1",
            "transition-colors",
            showHistory
              ? "bg-zinc-800 text-zinc-200"
              : ["text-zinc-400", "hover:text-zinc-300"].join(" "),
          ].join(" ")}
          title="Session history"
        >
          <History size={14} />
        </button>
      </div>

      {/* Session history */}
      {showHistory && (
        <div
          className="
            max-h-[200px]
            overflow-y-auto
            border-b border-zinc-800/60
            bg-[#141414]
            px-3 py-2
          "
        >
          <p
            className="
              mb-1.5
              text-[10px]
              font-medium
              uppercase
              tracking-wide
              text-zinc-400
            "
          >
            All sessions
          </p>

          {sessions.length > 0 ? (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={[
                  "flex w-full",
                  "cursor-pointer",
                  "items-center",
                  "rounded px-2 py-1",
                  "text-[11px]",
                  "transition-colors",
                  "hover:bg-zinc-800",
                  session.id === activeSessionId
                    ? "text-emerald-400"
                    : "text-zinc-400",
                ].join(" ")}
              >
                <span className="truncate">{session.title}</span>

                <span className="ml-auto text-[9px] text-zinc-600">
                  {new Date(session.created_at).toLocaleDateString()}
                </span>
              </button>
            ))
          ) : (
            <p className="text-[11px] text-zinc-400">No sessions yet</p>
          )}
        </div>
      )}

      {/* Chat */}
      <div className="min-h-0 flex-1">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <span className="text-xs text-zinc-500">Loading...</span>
          </div>
        ) : loadingMessages ? (
          <div className="flex h-full flex-col">
            <div className="flex-1 animate-pulse space-y-4 p-4">
              <div className="flex gap-2">
                <div className="h-7 w-7 shrink-0 rounded-full bg-zinc-800" />

                <div className="flex-1 space-y-1.5">
                  <div className="h-2.5 w-3/4 rounded bg-zinc-800" />
                  <div className="h-2.5 w-1/2 rounded bg-zinc-800" />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <div className="max-w-[70%] flex-1 space-y-1.5">
                  <div className="ml-auto h-2.5 w-full rounded bg-zinc-800" />
                  <div className="ml-auto h-2.5 w-2/3 rounded bg-zinc-800" />
                </div>
              </div>

              <div className="flex gap-2">
                <div className="h-7 w-7 shrink-0 rounded-full bg-zinc-800" />

                <div className="flex-1 space-y-1.5">
                  <div className="h-2.5 w-full rounded bg-zinc-800" />
                  <div className="h-2.5 w-4/5 rounded bg-zinc-800" />
                  <div className="h-2.5 w-2/5 rounded bg-zinc-800" />
                </div>
              </div>
            </div>
          </div>
        ) : activeSessionId ? (
          <div className="flex h-full flex-col">
            <div className="min-h-0 flex-1">
              <Conversation
                key={activeSessionId}
                initialMessages={initialMessages}
                sessionId={activeSessionId}
                fullScreen={false}
                transparentBg={false}
                recordId={recordId}
              />
            </div>
          </div>
        ) : (
          <div
            className="
              flex h-full
              flex-col
              items-center
              justify-center
              gap-3
              p-4
            "
          >
            <button
              onClick={() => void handleNewSession()}
              disabled={creatingSession}
              className="
                flex items-center gap-1.5
                text-xs
                text-zinc-400
                transition-colors
                hover:text-zinc-300
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
            >
              {creatingSession && (
                <Loader2 size={12} className="animate-spin" />
              )}

              {creatingSession
                ? "Starting…"
                : "Ask Tendo anything about your business or Start a new conversation session..."}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";

import { History, Loader2, Plus, X } from "lucide-react";

import { Conversation } from "../../pages/Conversation";

import { useBusinessStore } from "../../store/business";
import { useWorkspaceStore } from "../../store/workspace";

import {
  createSession,
  deleteSession,
  getSessionMessages,
  listSessions,
  type ChatSession,
} from "../../lib/services/conversations";

import type { MessageItem } from "./ConversationPage";

type Props = {
  recordId?: string;
};

const PAGE_SIZE = 20;

type SessionMessage = {
  role: string;
  content: string;
};

function mapMessages(
  messages: SessionMessage[],
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

  const requestIdRef = useRef(0);

  const pendingSessionRef = useRef<string | null>(null);

  const lastPendingMessageRef = useRef<string | null>(null);

  const loadMessagesForSession = useCallback(
    async (sessionId: string, requestId: number) => {
      if (!sessionId || !businessId) {
        return;
      }

      setLoadingMessages(true);
      setInitialMessages([]);

      const allMessages: MessageItem[] = [];
      let offset = 0;

      try {
        while (true) {
          const batch = await getSessionMessages(
            sessionId,
            businessId,
            PAGE_SIZE,
            offset,
          );

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

        if (requestId !== requestIdRef.current) {
          return;
        }

        setInitialMessages(allMessages);
      } catch {
        if (requestId !== requestIdRef.current) {
          return;
        }

        setInitialMessages([]);
      } finally {
        if (requestId === requestIdRef.current) {
          setLoadingMessages(false);
        }
      }
    },
    [businessId],
  );

  useEffect(() => {
    if (!businessId) {
      ++requestIdRef.current;

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

        setSessions(data);

        /*
         * The service returns the newest session first.
         */
        const newestSession = data[0];

        if (!newestSession) {
          setActiveSessionId("");
          setInitialMessages([]);
          return;
        }

        setActiveSessionId(newestSession.id);

        await loadMessagesForSession(newestSession.id, requestId);
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
   * Select an existing conversation.
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

      const requestId = ++requestIdRef.current;

      /*
       * Immediately clear the old conversation while
       * the new session is loading.
       */
      setActiveSessionId(sessionId);
      setInitialMessages([]);
      setLoadingMessages(true);
      setShowHistory(false);

      void loadMessagesForSession(sessionId, requestId);
    },
    [activeSessionId, loadMessagesForSession],
  );

  /*
   * Create a new empty conversation.
   */
  const handleNewSession = useCallback(async () => {
    if (!businessId || creatingSession) {
      return;
    }

    const requestId = ++requestIdRef.current;

    setCreatingSession(true);
    setShowHistory(false);
    setLoadingMessages(false);
    setInitialMessages([]);

    try {
      const session = await createSession(businessId, "New Session", recordId);

      if (requestId !== requestIdRef.current) {
        return;
      }

      setSessions((previous) => [
        session,
        ...previous.filter((item) => item.id !== session.id),
      ]);

      setActiveSessionId(session.id);
      setInitialMessages([]);
      setLoadingMessages(false);

      /*
       * If there is a pending workspace message, mark
       * this newly created session as its destination.
       */
      pendingSessionRef.current = pendingMsg ?? null;

      lastPendingMessageRef.current = pendingMsg ?? null;
    } catch {
      if (requestId !== requestIdRef.current) {
        return;
      }

      /*
       * Do not modify session state here.
       * The service owns the actual error handling.
       */
    } finally {
      if (requestId === requestIdRef.current) {
        setCreatingSession(false);
      }
    }
  }, [businessId, creatingSession, pendingMsg, recordId]);

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

    if (
      pendingSessionRef.current === pendingMsg ||
      lastPendingMessageRef.current === pendingMsg
    ) {
      return;
    }

    pendingSessionRef.current = pendingMsg;
    lastPendingMessageRef.current = pendingMsg;

    const requestId = ++requestIdRef.current;

    setCreatingSession(true);
    setInitialMessages([]);
    setLoadingMessages(false);

    const createPendingSession = async () => {
      try {
        const session = await createSession(
          businessId,
          "New Session",
          recordId,
        );

        if (requestId !== requestIdRef.current) {
          return;
        }

        setSessions((previous) => [
          session,
          ...previous.filter((item) => item.id !== session.id),
        ]);

        setActiveSessionId(session.id);
        setInitialMessages([]);
        setLoadingMessages(false);
      } catch {
        if (requestId === requestIdRef.current) {
          pendingSessionRef.current = null;
          lastPendingMessageRef.current = null;
        }
      } finally {
        if (requestId === requestIdRef.current) {
          setCreatingSession(false);
        }
      }
    };

    void createPendingSession();
  }, [
    pendingMsg,
    businessId,
    loading,
    creatingSession,
    activeSessionId,
    recordId,
  ]);

  /*
   * Delete a conversation.
   *
   * Deleting an inactive session must NOT invalidate
   * a message request for the currently active session.
   */
  const handleCloseSession = useCallback(
    async (sessionId: string) => {
      if (!sessionId || !businessId) {
        return;
      }

      const wasActive = sessionId === activeSessionId;

      const remainingSessions = sessions.filter(
        (session) => session.id !== sessionId,
      );

      /*
       * Only invalidate the active request when the
       * deleted session is actually active.
       */
      if (wasActive) {
        ++requestIdRef.current;

        const nextSession = remainingSessions[0];

        setSessions(remainingSessions);
        setInitialMessages([]);
        setLoadingMessages(false);
        setActiveSessionId(nextSession?.id ?? "");

        /*
         * If another session exists, load it explicitly.
         */
        if (nextSession) {
          const requestId = ++requestIdRef.current;

          setLoadingMessages(true);

          void loadMessagesForSession(nextSession.id, requestId);
        }
      } else {
        setSessions(remainingSessions);
      }

      try {
        await deleteSession(sessionId, businessId);
      } catch {
        /*
         * Keep the optimistic UI.
         * The service owns the underlying error.
         */
      }
    },
    [activeSessionId, businessId, loadMessagesForSession, sessions],
  );

  /*
   * Collapsed state.
   */
  if (collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        className="
          flex h-full w-10
          items-center justify-center
          border-l border-zinc-800/60
          bg-[#0f0f0f]
          text-zinc-400
          transition-colors
          hover:text-zinc-300
        "
        title="Open chat"
        aria-label="Open chat"
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
        {sessions.slice(0, 5).map((session) => {
          const isActive = session.id === activeSessionId;

          return (
            <div
              key={session.id}
              className={[
                "flex shrink-0 items-center gap-1",
                "rounded-t-md px-2.5 py-1.5",
                "text-[11px]",
                "transition-colors",
                isActive
                  ? [
                      "border border-zinc-800/60",
                      "border-b-transparent",
                      "bg-[#0f0f0f]",
                      "text-zinc-200",
                    ].join(" ")
                  : ["text-zinc-400", "hover:text-zinc-300"].join(" "),
              ].join(" ")}
            >
              <button
                type="button"
                onClick={() => handleSelectSession(session.id)}
                className="
                  min-w-0 max-w-[100px]
                  truncate
                  text-left
                "
                title={session.title}
              >
                {session.title}
              </button>

              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  void handleCloseSession(session.id);
                }}
                className="
                  ml-0.5 shrink-0
                  rounded p-0.5
                  text-zinc-500
                  transition-colors
                  hover:bg-zinc-800
                  hover:text-zinc-300
                "
                title="Close session"
                aria-label={`Close ${session.title}`}
              >
                <X size={10} />
              </button>
            </div>
          );
        })}

        <button
          type="button"
          onClick={() => void handleNewSession()}
          disabled={creatingSession}
          className="
            flex shrink-0 items-center gap-1
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
          type="button"
          onClick={() => setShowHistory((previous) => !previous)}
          className={[
            "shrink-0 rounded p-1",
            "transition-colors",
            showHistory
              ? "bg-zinc-800 text-zinc-200"
              : ["text-zinc-400", "hover:text-zinc-300"].join(" "),
          ].join(" ")}
          title="Session history"
          aria-label="Session history"
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
              text-zinc-500
            "
          >
            All sessions
          </p>

          {sessions.length > 0 ? (
            <div className="space-y-0.5">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => handleSelectSession(session.id)}
                  className={[
                    "flex w-full items-center",
                    "rounded px-2 py-1",
                    "text-[11px]",
                    "transition-colors",
                    "hover:bg-zinc-800",
                    session.id === activeSessionId
                      ? "text-emerald-400"
                      : "text-zinc-400",
                  ].join(" ")}
                >
                  <span className="min-w-0 truncate">{session.title}</span>

                  <span className="ml-auto shrink-0 pl-2 text-[9px] text-zinc-600">
                    {new Date(session.created_at).toLocaleDateString()}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-zinc-500">No sessions yet</p>
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
              text-center
            "
          >
            <button
              type="button"
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
                : "Ask Tendo anything about your business or start a new conversation session..."}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

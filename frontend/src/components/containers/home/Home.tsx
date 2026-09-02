import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ChatPanel } from "../../../components/containers/ChatPanel";
import { useWorkspaceStore } from "../../../store/workspace";
import type { InboxMessage } from "./types";
import { HomeBriefing } from "./HomeBriefing";
import { MessageDetail } from "./MessageDetail";
import { useHomeData } from "./useHomeData";

function getFirstName(profile: any): string {
  const candidates = [
    profile?.user?.name,
    profile?.owner?.name,
    profile?.owner_name,
    profile?.user_name,
    profile?.full_name,
  ];

  const name = candidates.find(
    (value) => typeof value === "string" && value.trim(),
  );

  return name ? name.trim().split(/\s+/)[0] : "there";
}

const DEFAULT_CHAT_WIDTH = 360;
const MIN_CHAT_WIDTH = 320;
const MAX_CHAT_WIDTH = 600;

export function Home() {
  const [openMessage, setOpenMessage] = useState<InboxMessage | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH);
  const [isResizingChat, setIsResizingChat] = useState(false);

  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(DEFAULT_CHAT_WIDTH);

  const {
    currentProfile,
    recentRecords,
    insights,
    attention,
    loading,
    recordsTotal,
    recordsOffset,
    refresh,
    loadMoreRecords,
    markRecordRead,
    deleteRecord,
  } = useHomeData();

  useEffect(() => {
    const handleOpenRecord = (event: Event) => {
      const detail = (event as CustomEvent).detail;

      if (!detail?.id) return;

      const existing = recentRecords.find(
        (record) => record.id === `record-${detail.id}`,
      );

      setOpenMessage(
        existing || {
          id: `record-${detail.id}`,
          sender: detail.title || "Untitled",
          senderEmail: "",
          recipient: "",
          subject: detail.title || "Untitled",
          preview: "",
          body: "",
          date: detail.created_at || new Date().toISOString(),
          fullDate: detail.created_at || new Date().toISOString(),
          read: true,
          starred: false,
          tab: "primary",
          avatarColor: "bg-zinc-600",
        },
      );
    };

    window.addEventListener("tendo:open-record-detail", handleOpenRecord);

    return () => {
      window.removeEventListener("tendo:open-record-detail", handleOpenRecord);
    };
  }, [recentRecords]);

  const askTendo = (message: string) => {
    useWorkspaceStore.getState().setPendingChatMessage(message);
  };

  const reviewSnap = (snap: any) => {
    const title = snap.title || snap.message || "this item";

    askTendo(
      `Help me review this: ${title}${
        snap.action ? `\n\nSuggested action: ${snap.action}` : ""
      }`,
    );
  };

  const refreshHome = async () => {
    setRefreshing(true);

    try {
      await refresh();
    } finally {
      setRefreshing(false);
    }
  };

  /**
   * Start resizing the ChatPanel.
   */
  const handleResizeStart = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();

    resizeStartXRef.current = event.clientX;
    resizeStartWidthRef.current = chatWidth;

    setIsResizingChat(true);

    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  /**
   * Resize while dragging.
   *
   * Because the ChatPanel is on the right side, moving the divider
   * to the left makes the panel wider and moving it right makes
   * the panel narrower.
   */
  useEffect(() => {
    if (!isResizingChat) return;

    const handlePointerMove = (event: PointerEvent) => {
      const delta = resizeStartXRef.current - event.clientX;

      const nextWidth = Math.min(
        MAX_CHAT_WIDTH,
        Math.max(MIN_CHAT_WIDTH, resizeStartWidthRef.current + delta),
      );

      setChatWidth(nextWidth);
    };

    const handlePointerUp = () => {
      setIsResizingChat(false);
    };

    document.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerup", handlePointerUp);

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerup", handlePointerUp);

      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizingChat]);

  if (openMessage) {
    const currentIndex = recentRecords.findIndex(
      (item) => item.id === openMessage.id,
    );

    const hasMore = recordsOffset < recordsTotal;

    return (
      <MessageDetail
        message={openMessage}
        onBack={() => setOpenMessage(null)}
        currentIndex={currentIndex >= 0 ? currentIndex : 0}
        totalMessages={hasMore ? recordsTotal : recentRecords.length}
        onPrev={() => {
          if (currentIndex > 0) {
            setOpenMessage(recentRecords[currentIndex - 1]);
          }
        }}
        onNext={async () => {
          if (currentIndex >= 0 && currentIndex < recentRecords.length - 1) {
            setOpenMessage(recentRecords[currentIndex + 1]);
            return;
          }

          if (hasMore) {
            await loadMoreRecords();
          }
        }}
        onDelete={async () => {
          await deleteRecord(openMessage.id);
          setOpenMessage(null);
        }}
      />
    );
  }

  return (
    <div className="flex h-full min-h-0 bg-[#0a0a0a] text-zinc-100">
      {/* Main briefing */}
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-[900px] flex-col">
          {/* Page actions */}
          <div className="flex items-center justify-end px-6 pt-5 lg:px-10">
            <button
              type="button"
              onClick={refreshHome}
              disabled={refreshing}
              aria-label="Refresh home"
              title="Refresh"
              className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-600 transition-colors hover:bg-white/5 hover:text-zinc-300 disabled:opacity-40"
            >
              <RefreshCw
                size={15}
                className={refreshing ? "animate-spin" : ""}
              />
            </button>
          </div>

          <div className="px-6 pt-1 lg:px-10">
            <div className="mx-auto w-full max-w-3xl">
              <HomeBriefing
                firstName={getFirstName(currentProfile)}
                attention={attention}
                insights={insights}
                recentRecords={recentRecords}
                activityCount={recordsTotal}
                onAsk={askTendo}
                onOpenRecord={(record) => {
                  markRecordRead(record.id);
                  setOpenMessage(record);
                }}
                onReview={reviewSnap}
              />

              <div className="mb-10" />
            </div>
          </div>
        </div>
      </main>

      {/* Tendo colleague panel */}
      <aside
        style={{ width: `${chatWidth}px` }}
        className="relative hidden shrink-0 border-l border-zinc-800/60 bg-[#0f0f0f] lg:flex lg:flex-col"
      >
        {/* Resize handle */}
        <div
          role="separator"
          aria-label="Resize Tendo panel"
          aria-orientation="vertical"
          onPointerDown={handleResizeStart}
          className={`absolute left-0 top-0 z-30 h-full w-1 -translate-x-1/2 cursor-col-resize transition-colors ${
            isResizingChat
              ? "bg-emerald-500/50"
              : "bg-transparent hover:bg-zinc-700/60"
          }`}
        />

        <div className="min-h-0 flex-1">
          <ChatPanel />
        </div>
      </aside>

      {/* Background refresh state */}
      {loading && (
        <div className="pointer-events-none fixed bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-zinc-800/70 bg-[#111111]/90 px-3 py-1.5 text-[10px] text-zinc-600 backdrop-blur">
          Updating
        </div>
      )}
    </div>
  );
}

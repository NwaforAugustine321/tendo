import { useState, useEffect, useCallback, useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  Trash2,
  Sparkles,
  Type,
  Image,
  Mic,
  FileText,
  Plus as PlusIcon,
  ChevronDown as ChevronDownIcon,
} from "lucide-react";
import clsx from "clsx";
import { ChatPanel } from "../../../components/containers/ChatPanel";
import { AiDisplay } from "../../../components/atoms/AiDisplay";
import {
  EXPLAIN_PROMPT,
  explainPrompt,
} from "../../../lib/workspace/constants";
import { useBusinessStore } from "../../../store/business";
import { useWorkspaceStore } from "../../../store/workspace";
import * as recordsApi from "../../../lib/services/records";
import { useEventReceiver } from "../../../hooks/useEmitReceiver";
import {
  showProcessingToast,
  dismissProcessingToast,
} from "../../../components/atoms/ProcessingNotification";
import { toast } from "sonner";
import { checkUpload } from "../../../lib/uploadLimits";
import type { InboxMessage, InboxTab } from "./types";
import { formatRelativeTime, snapToSender, snapTypeToColor } from "./helpers";
import type { Snap } from "../../../lib/services/snaps";

function Tag({
  children,
  label,
  className,
}: {
  children: React.ReactNode;
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium capitalize leading-none",
        className || "border-zinc-700/50 bg-zinc-800/40 text-zinc-400",
      )}
    >
      {label && <span className="normal-case opacity-60">{label}: </span>}
      {children}
    </span>
  );
}

function snapToMessage(snap: Snap, tab: InboxTab): InboxMessage {
  const urgent = snap.priority === "high" || snap.priority === "critical";
  return {
    id: `snap-${snap.snap_id}`,
    sender: snapToSender(snap.type, snap.domain),
    senderEmail: "",
    recipient: "",
    subject: snap.message,
    preview: snap.action,
    body: [snap.title, snap.message, snap.why_it_matters, snap.action]
      .filter(Boolean)
      .join("\n\n"),
    date: snap.created_at ? formatRelativeTime(snap.created_at) : "Just now",
    fullDate: snap.created_at
      ? new Date(snap.created_at).toLocaleString()
      : new Date().toLocaleString(),
    read: !urgent,
    starred: snap.priority === "critical",
    tab,
    avatarColor: snapTypeToColor(snap.type),
    snapId: snap.snap_id,
    snapPriority: snap.priority,
    snapDomain: snap.domain,
  };
}

// --- Collapsible Section ---

function CollapsibleSection({
  title,
  subtitle,
  avatarColor,
  defaultOpen = false,
  icon,
  processing,
  children,
}: {
  title: string;
  subtitle: string;
  avatarColor: string;
  defaultOpen?: boolean;
  icon?: string;
  processing?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const renderIcon = () => {
    if (processing)
      return (
        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-zinc-600 border-t-emerald-500" />
      );
    switch (icon) {
      case "text":
        return <Type size={14} className="text-zinc-400" />;
      case "image":
        return <Image size={14} className="text-zinc-400" />;
      case "audio":
        return <Mic size={14} className="text-zinc-400" />;
      case "pdf":
        return <FileText size={14} className="text-zinc-400" />;
      default:
        return <Type size={14} className="text-zinc-400" />;
    }
  };

  return (
    <div className="mb-4 bg-zinc-900/20 rounded-lg border border-zinc-800/20">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <span className="shrink-0">{renderIcon()}</span>
        <div className="min-w-0 flex-1">
          <span className="text-[13px] font-medium text-zinc-200 line-clamp-1">
            {title}
          </span>
          {processing && (
            <span className="text-[11px] text-zinc-500 ml-2">
              Processing...
            </span>
          )}
        </div>
        {!processing && (
          <span className="text-[11px] text-zinc-500 shrink-0 mr-2">
            {subtitle}
          </span>
        )}
        <ChevronDownIcon
          size={16}
          className={clsx(
            "text-zinc-500 transition-transform shrink-0",
            !open && "-rotate-90",
          )}
        />
      </button>
      {open && <div className="px-4 pb-4 pt-0">{children}</div>}
    </div>
  );
}

// --- Summary text + "Ask Tendo" link ---

/**
 * A summary only exists once processing has produced text.
 * Raw data URLs and the processing placeholder are not summaries.
 */
function hasSummary(text: string | undefined | null): boolean {
  if (!text) return false;
  const value = text.trim();
  if (!value) return false;
  if (value.startsWith("data:")) return false;
  if (value.startsWith("[Processing")) return false;
  return true;
}

function SummaryBlock({
  summary,
  textClass = "text-[13px]",
}: {
  summary: string;
  textClass?: string;
}) {
  if (!hasSummary(summary)) return null;

  return (
    <div className={clsx("leading-relaxed text-zinc-300", textClass)}>
      <span className="whitespace-pre-wrap">{summary}</span>{" "}
      <button
        type="button"
        onClick={() =>
          useWorkspaceStore
            .getState()
            .setPendingChatMessage(explainPrompt(summary))
        }
        title="Ask Tendo to explain this summary in the open chat session"
        className="inline-flex items-baseline align-baseline text-[10px] text-[#3ecf8e] underline hover:text-[#3ecf8e]/80 transition-colors"
      >
        Ask Tendo about this document.
      </button>
    </div>
  );
}

// --- Message Detail View ---

export function MessageDetail({
  message,
  onBack,
  currentIndex,
  totalMessages,
  onPrev,
  onNext,
  onDelete,
}: {
  message: InboxMessage;
  onBack: () => void;
  currentIndex: number;
  totalMessages: number;
  onPrev: () => void;
  onNext: () => void;
  onDelete?: () => void | Promise<void>;
}) {
  const [contents, setContents] = useState<
    {
      id: string;
      content_type: string;
      content: string;
      file_url?: string;
      created_at: string;
      _processing?: boolean;
      _fileName?: string;
    }[]
  >([]);
  const [addingType, setAddingType] = useState<string | null>(null);
  const [newContent, setNewContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recordId = message.id.startsWith("record-")
    ? message.id.replace("record-", "")
    : "";
  const [insight, setInsight] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [loadingInsight, setLoadingInsight] = useState(true);
  const [insightExpanded, setInsightExpanded] = useState(false);
  const insightPanelRef = useRef<HTMLDivElement>(null);
  const [panelPos, setPanelPos] = useState<{ x: number; y: number } | null>(
    null,
  );
  const dragging = useRef(false);
  const dragOffset = useRef({ x: 0, y: 0 });
  const contentScrollRef = useRef<HTMLDivElement>(null);
  const pollIntervalsRef = useRef<Map<string, ReturnType<typeof setInterval>>>(
    new Map(),
  );

  // Chat panel resize state
  const [chatPanelWidth, setChatPanelWidth] = useState(340);
  const chatResizing = useRef(false);
  const chatResizeStartX = useRef(0);
  const chatResizeStartWidth = useRef(340);

  const handleChatResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      chatResizing.current = true;
      chatResizeStartX.current = e.clientX;
      chatResizeStartWidth.current = chatPanelWidth;

      const handleMouseMove = (ev: MouseEvent) => {
        if (!chatResizing.current) return;
        const delta = chatResizeStartX.current - ev.clientX;
        const newWidth = Math.min(
          600,
          Math.max(280, chatResizeStartWidth.current + delta),
        );
        setChatPanelWidth(newWidth);
      };

      const handleMouseUp = () => {
        chatResizing.current = false;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [chatPanelWidth],
  );

  // Clamp panel to viewport when it expands/collapses
  useEffect(() => {
    const el = insightPanelRef.current;
    if (!el) return;
    requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect();
      const h = window.innerHeight;
      let newY = panelPos ? panelPos.y : undefined;
      let newX = panelPos ? panelPos.x : undefined;
      if (rect.bottom > h - 10) {
        newY = h - rect.height - 10;
      }
      if (rect.top < 10) {
        newY = 10;
      }
      if (newY !== undefined && newX !== undefined) {
        setPanelPos({ x: newX, y: newY });
      } else if (newY !== undefined) {
        setPanelPos((prev) => (prev ? { ...prev, y: newY! } : null));
      }
    });
  }, [insightExpanded, insight, suggestedQuestions]);

  const handlePanelMouseDown = (e: React.MouseEvent) => {
    const el = insightPanelRef.current;
    if (!el) return;
    dragging.current = true;
    const rect = el.getBoundingClientRect();
    dragOffset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      let x = ev.clientX - dragOffset.current.x;
      let y = ev.clientY - dragOffset.current.y;
      if (x < 0) x = 0;
      if (y < 0) y = 0;
      if (x + 280 > w) x = w - 280;
      const elH = el.getBoundingClientRect().height;
      if (y + elH > h) y = h - elH - 10;
      setPanelPos({ x, y });
    };
    const onUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  // Fetch insight via API
  useEffect(() => {
    if (!recordId) {
      setLoadingInsight(false);
      return;
    }

    const { currentProfile } = useBusinessStore.getState();
    const businessId = currentProfile?.id || "";
    if (!businessId) {
      setLoadingInsight(false);
      return;
    }

    setLoadingInsight(true);
    recordsApi
      .getRecordUnderstanding(recordId)
      .then((data) => {
        if (data?.insight) {
          setInsight(data.insight);
          setSuggestedQuestions(data?.suggestions || []);
        }
        setLoadingInsight(false);
      })
      .catch(() => {
        setLoadingInsight(false);
      });
  }, [recordId]);

  const { events: documentProgressEvents } = useEventReceiver([
    "document.progress",
  ]);

  // Handle document.progress events — update insights and stop polling
  useEffect(() => {
    if (documentProgressEvents.length === 0) return;
    const latest = documentProgressEvents[documentProgressEvents.length - 1];
    const data = latest.data as any;
    const status = (data?.status || "").toLowerCase();
    if (status === "completed") {
      if (data?.data?.summary) {
        setInsight(data.data.summary);
      }
      if (data?.data?.suggested_questions?.length) {
        setSuggestedQuestions(data.data.suggested_questions);
      }
      setLoadingInsight(false);
      pollIntervalsRef.current.forEach((interval) => clearInterval(interval));
      pollIntervalsRef.current.clear();
      setContents((prev) =>
        prev.map((c) => (c._processing ? { ...c, _processing: false } : c)),
      );
      if (recordId) {
        recordsApi
          .getRecordContents(recordId)
          .then((updated) => {
            setContents(updated);
          })
          .catch(() => {});
      }
    } else if (status === "failed") {
      pollIntervalsRef.current.forEach((interval) => clearInterval(interval));
      pollIntervalsRef.current.clear();
      setContents((prev) =>
        prev.map((c) => (c._processing ? { ...c, _processing: false } : c)),
      );
      if (recordId) {
        recordsApi
          .getRecordContents(recordId)
          .then((updated) => {
            setContents(updated);
          })
          .catch(() => {});
      }
    }
  }, [documentProgressEvents, recordId]);

  // Auto-scroll to bottom when new content is added
  useEffect(() => {
    if (contentScrollRef.current && contents.length > 0) {
      setTimeout(() => {
        contentScrollRef.current?.scrollTo({
          top: contentScrollRef.current.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    }
  }, [contents.length]);

  // Fetch all record contents on mount
  useEffect(() => {
    if (!recordId) {
      setLoadingContent(false);
      return;
    }
    // Clear any existing poll intervals from previous recordId
    pollIntervalsRef.current.forEach((interval) => clearInterval(interval));
    pollIntervalsRef.current.clear();

    setLoadingContent(true);
    recordsApi
      .getRecordContents(recordId)
      .then((data) => {
        setContents(data);

        // Resume polling for any content still processing (status === 'processing')
        data.forEach((c: any) => {
          if (c.status === "processing" && c.id) {
            const pollInterval = setInterval(async () => {
              try {
                const updated = await recordsApi.getRecordContents(recordId);
                const found = updated.find((u: any) => u.id === c.id);
                if (found && found.status !== "processing") {
                  clearInterval(pollInterval);
                  pollIntervalsRef.current.delete(c.id);
                  dismissProcessingToast("Document processed");
                  setContents((prev) =>
                    prev.map((p) =>
                      p.id === c.id ? { ...found, _processing: false } : p,
                    ),
                  );
                  if (found.content) {
                    setInsight(found.content);
                    setLoadingInsight(false);
                  }
                }
              } catch {
                /* retry */
              }
            }, 4000);
            pollIntervalsRef.current.set(c.id, pollInterval);
            // Mark as processing in UI
            setContents((prev) =>
              prev.map((p) =>
                p.id === c.id
                  ? { ...p, _processing: true, _fileName: c.content_type }
                  : p,
              ),
            );
          }
        });
      })
      .catch(() => {})
      .finally(() => setLoadingContent(false));

    return () => {
      pollIntervalsRef.current.forEach((interval) => clearInterval(interval));
      pollIntervalsRef.current.clear();
    };
  }, [recordId]);

  useEffect(() => {
    if (addingType === "text")
      setTimeout(() => textareaRef.current?.focus(), 50);
  }, [addingType]);

  const handleAddContent = (type: string) => {
    if (type === "text") {
      setAddingType(type);
      setNewContent("");
    }
    // For file types, the hidden input handles it directly
  };

  const handleFileSelected = async (type: string, file: File) => {
    const limitError = await checkUpload(type, file);
    if (limitError) {
      toast.error(limitError);
      return;
    }

    const fileName = file.name || `${type} file`;

    // Show card + toast IMMEDIATELY before upload
    const tempId = crypto.randomUUID();
    setContents((prev) => [
      ...prev,
      {
        id: tempId,
        content_type: type,
        content: "",
        file_url: "",
        created_at: new Date().toISOString(),
        _processing: true,
        _fileName: fileName,
      },
    ]);

    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result as string;
      setSaving(true);
      try {
        const result = await recordsApi.addRecordContent(
          recordId,
          type,
          base64,
        );
        showProcessingToast("Processing document...");
        const contentId = result.content.id;

        // Replace temp card with real one
        setContents((prev) =>
          prev.map((c) =>
            c.id === tempId
              ? {
                  id: contentId,
                  content_type: type,
                  content: "",
                  file_url: result.content.file_url || "",
                  created_at: new Date().toISOString(),
                  _processing: true,
                  _fileName: fileName,
                }
              : c,
          ),
        );

        // Poll for completion
        const pollInterval = setInterval(async () => {
          try {
            const updated = await recordsApi.getRecordContents(recordId);
            const found = updated.find((c: any) => c.id === contentId);
            if (found && found.status !== "processing") {
              clearInterval(pollInterval);
              pollIntervalsRef.current.delete(contentId);
              dismissProcessingToast("Document processed");
              setContents((prev) =>
                prev.map((c) =>
                  c.id === contentId ? { ...found, _processing: false } : c,
                ),
              );
              if (found.content) {
                setInsight(found.content);
                setLoadingInsight(false);
              }
            }
          } catch {
            /* retry */
          }
        }, 4000);
        pollIntervalsRef.current.set(contentId, pollInterval);
      } catch {
        setContents((prev) => prev.filter((c) => c.id !== tempId));
      } finally {
        setSaving(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSaveContent = async () => {
    if (!recordId || !newContent.trim() || !addingType) return;
    setSaving(true);
    try {
      const result = await recordsApi.addRecordContent(
        recordId,
        addingType,
        newContent.trim(),
      );
      showProcessingToast("Processing content...");
      const contentId = result.content.id;
      setContents((prev) => [
        ...prev,
        {
          id: contentId,
          content_type: addingType,
          content: newContent.trim(),
          created_at: new Date().toISOString(),
          _processing: true,
          _fileName: "Text note",
        },
      ]);
      setAddingType(null);
      setNewContent("");

      // Poll for processing completion
      const pollInterval = setInterval(async () => {
        try {
          const updated = await recordsApi.getRecordContents(recordId);
          const found = updated.find((c: any) => c.id === contentId);
          if (found && found.status !== "processing") {
            clearInterval(pollInterval);
            pollIntervalsRef.current.delete(contentId);
            dismissProcessingToast("Document processed");
            setContents((prev) =>
              prev.map((c) =>
                c.id === contentId ? { ...found, _processing: false } : c,
              ),
            );
            if (found.content) {
              setInsight(found.content);
              setLoadingInsight(false);
            }
          }
        } catch {
          /* retry */
        }
      }, 4000);
      pollIntervalsRef.current.set(contentId, pollInterval);
    } catch {
      toast.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full bg-[#0a0a0a]">
      {/* Left: Record detail */}
      <div className="flex min-w-0 flex-1 flex-col relative">
        {/* Detail toolbar */}
        <div className="flex items-center gap-1 border-b border-zinc-800/60 px-4 py-2">
          <button
            type="button"
            onClick={onBack}
            className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200"
            aria-label="Back"
          >
            <ArrowLeft size={18} />
          </button>
          <button
            type="button"
            onClick={() => void onDelete?.()}
            className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
            aria-label="Delete"
          >
            <Trash2 size={16} />
          </button>
          <div className="flex-1" />
          <span className="text-[12px] text-zinc-500">
            {currentIndex + 1} of {totalMessages}
          </span>
          <button
            type="button"
            onClick={onPrev}
            disabled={currentIndex <= 0}
            className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Previous"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={currentIndex >= totalMessages - 1}
            className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Next"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Content */}
        <div
          ref={contentScrollRef}
          className="flex-1 overflow-y-auto px-6 py-4"
        >
          {/* Subject */}
          <div className="flex items-center gap-2 mb-4">
            <h1 className="text-[18px] font-normal text-zinc-100">
              {message.sender}
            </h1>
          </div>

          {/* Insight panel — draggable floating, defaults to bottom-right of left column */}
          <div
            ref={insightPanelRef}
            className="fixed w-[350px] z-[9999] cursor-move select-none"
            style={
              panelPos
                ? { left: panelPos.x, top: panelPos.y }
                : { bottom: "70px", right: "356px" }
            }
            onMouseDown={handlePanelMouseDown}
          >
            <div className="rounded-lg border border-zinc-800/40 bg-[#141414] p-3">
              {loadingInsight ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={11} className="text-emerald-500" />
                    <span className="text-[10px] font-medium text-zinc-400">
                      Overview
                    </span>
                  </div>
                  <div className="animate-pulse space-y-1.5">
                    <div className="h-2.5 w-full rounded bg-zinc-800" />
                    <div className="h-2.5 w-4/5 rounded bg-zinc-800" />
                    <div className="h-2.5 w-3/5 rounded bg-zinc-800" />
                  </div>
                  <div className="flex gap-1.5 mt-2">
                    <button
                      type="button"
                      onClick={() => {
                        useWorkspaceStore
                          .getState()
                          .setPendingChatMessage(EXPLAIN_PROMPT);
                      }}
                      className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[9px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                    >
                      <Sparkles size={8} />
                      <span>Ask Tendo about this document.</span>
                    </button>
                  </div>
                </div>
              ) : insight ? (
                <>
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Sparkles size={11} className="text-emerald-500" />
                    <span className="text-[10px] font-medium text-zinc-400">
                      Overview
                    </span>
                  </div>
                  <div
                    className={clsx(
                      "overflow-hidden transition-all duration-200",
                      insightExpanded
                        ? "max-h-[300px] overflow-y-auto"
                        : "max-h-[90px]",
                    )}
                  >
                    <AiDisplay
                      content={insight || ""}
                      className="text-[11px] leading-relaxed text-zinc-300"
                    />
                  </div>
                  {insight.length > 120 && (
                    <button
                      type="button"
                      onClick={() => setInsightExpanded(!insightExpanded)}
                      className="mt-1 text-[10px] text-[#3ecf8e] hover:text-[#3ecf8e]/80 transition-colors"
                    >
                      {insightExpanded ? "See less" : "See more"}
                    </button>
                  )}
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {suggestedQuestions.map((q, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          useWorkspaceStore.getState().setPendingChatMessage(q);
                        }}
                        className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-zinc-700/50 bg-[#1a1a1a] text-[9px] text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
                      >
                        <Sparkles
                          size={8}
                          className="text-[#3ecf8e] shrink-0"
                        />
                        <span>{q}</span>
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        useWorkspaceStore
                          .getState()
                          .setPendingChatMessage(EXPLAIN_PROMPT);
                      }}
                      className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[9px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                    >
                      <Sparkles size={8} />
                      <span>Ask Tendo about this document.</span>
                    </button>
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={11} className="text-emerald-500" />
                    <span className="text-[10px] text-zinc-500">
                      No insights yet
                    </span>
                  </div>
                  {suggestedQuestions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {suggestedQuestions.map((q, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            useWorkspaceStore
                              .getState()
                              .setPendingChatMessage(q);
                          }}
                          className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-zinc-700/50 bg-[#1a1a1a] text-[9px] text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
                        >
                          <Sparkles
                            size={8}
                            className="text-[#3ecf8e] shrink-0"
                          />
                          <span>{q}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      useWorkspaceStore
                        .getState()
                        .setPendingChatMessage(EXPLAIN_PROMPT);
                    }}
                    className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[9px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                  >
                    <Sparkles size={8} />
                    <span>Ask Tendo about this document.</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Record contents — each as collapsible */}
          {contents.length > 0 ? (
            contents.map((content, idx) => (
              <CollapsibleSection
                key={content.id}
                title={
                  content._processing
                    ? content._fileName || "Processing..."
                    : (content as any).title
                      ? (content as any).title.slice(0, 60) +
                        ((content as any).title.length > 60 ? "..." : "")
                      : content.content &&
                          !content.content.startsWith("data:") &&
                          !content.content.startsWith("[Processing")
                        ? content.content.slice(0, 60) +
                          (content.content.length > 60 ? "..." : "")
                        : content._fileName ||
                          content.content_type.charAt(0).toUpperCase() +
                            content.content_type.slice(1)
                }
                subtitle={
                  content._processing
                    ? ""
                    : formatRelativeTime(content.created_at)
                }
                avatarColor="bg-zinc-600"
                defaultOpen={idx === 0 || idx === contents.length - 1}
                icon={content.content_type}
                processing={content._processing}
              >
                {["image", "png", "jpg", "jpeg", "webp"].includes(
                  content.content_type,
                ) &&
                (content.file_url ||
                  content.content.startsWith("data:image")) ? (
                  <div className="flex items-start gap-3">
                    <a
                      href={content.file_url || content.content}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0"
                    >
                      <img
                        src={content.file_url || content.content}
                        alt="Uploaded image"
                        className="max-w-[150px] max-h-[100px] rounded-md cursor-pointer hover:opacity-80 transition-opacity"
                      />
                    </a>
                    <SummaryBlock summary={content.content} />
                  </div>
                ) : [
                    "audio",
                    "mp3",
                    "wav",
                    "m4a",
                    "ogg",
                    "aac",
                    "flac",
                    "wma",
                    "mpeg",
                  ].includes(content.content_type) &&
                  (content.file_url ||
                    content.content.startsWith("data:audio")) ? (
                  <div className="flex flex-col gap-2">
                    <audio
                      controls
                      src={content.file_url || content.content}
                      className="w-[280px]"
                    />
                    <SummaryBlock summary={content.content} />
                  </div>
                ) : content.content_type === "pdf" ? (
                  <div className="flex items-start gap-3">
                    {content.file_url && (
                      <a
                        href={content.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0"
                      >
                        <object
                          data={content.file_url}
                          type="application/pdf"
                          className="max-w-[150px] max-h-[100px] rounded-md pointer-events-none"
                        >
                          <div className="w-[150px] h-[100px] rounded-md bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                            <FileText size={32} className="text-zinc-400" />
                          </div>
                        </object>
                      </a>
                    )}
                    <SummaryBlock summary={content.content} />
                  </div>
                ) : hasSummary(content.content) ? (
                  <SummaryBlock
                    summary={content.content}
                    textClass="text-[14px]"
                  />
                ) : (
                  <div className="text-[14px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                    {content.content}
                  </div>
                )}
              </CollapsibleSection>
            ))
          ) : !addingType ? (
            loadingContent ? (
              <div className="space-y-3 animate-pulse py-4">
                <div
                  className="rounded-lg border border-zinc-800/40 bg-zinc-900/30 p-4"
                  style={{ overflow: "auto" }}
                >
                  <div className="h-2.5 w-full rounded bg-zinc-800 mb-2" />
                  <div className="h-2.5 w-3/4 rounded bg-zinc-800 mb-2" />
                  <div className="h-2.5 w-1/2 rounded bg-zinc-800" />
                </div>
                <div
                  className="rounded-lg border border-zinc-800/40 bg-zinc-900/30 p-4"
                  style={{ overflow: "auto" }}
                >
                  <div className="h-2.5 w-full rounded bg-zinc-800 mb-2" />
                  <div className="h-2.5 w-2/3 rounded bg-zinc-800" />
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-[13px] text-zinc-500">
                No content yet. Add some below.
              </div>
            )
          ) : null}

          {/* New content input area — text only */}
          {addingType === "text" && (
            <div className="mt-4 rounded-lg border border-zinc-800/40 bg-zinc-900/30 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[11px] uppercase tracking-wide text-zinc-500">
                  text
                </span>
              </div>
              <textarea
                ref={textareaRef}
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && e.metaKey) handleSaveContent();
                }}
                placeholder="Type your content here... (⌘+Enter to save)"
                className="w-full min-h-[100px] resize-none bg-transparent text-[13px] leading-relaxed text-zinc-200 placeholder-zinc-600 focus:outline-none"
              />
              <div className="flex items-center gap-2 mt-3">
                <button
                  type="button"
                  onClick={handleSaveContent}
                  disabled={!newContent.trim() || saving}
                  className="rounded-md bg-emerald-600 px-3 py-1 text-[11px] font-medium text-white hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAddingType(null);
                    setNewContent("");
                  }}
                  className="rounded-md px-3 py-1 text-[11px] font-medium text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Fixed bottom — source input buttons */}
        <div className="shrink-0 flex items-center gap-2 px-6 py-3 border-t border-zinc-800/40 flex-wrap">
          <button
            type="button"
            onClick={() => handleAddContent("text")}
            className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200"
          >
            <Type size={14} /> Text
          </button>
          <label className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200 cursor-pointer">
            <Image size={14} /> Image
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelected("image", f);
                e.target.value = "";
              }}
            />
          </label>
          <label className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200 cursor-pointer">
            <Mic size={14} /> Audio
            <input
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelected("audio", f);
                e.target.value = "";
              }}
            />
          </label>
          <label className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200 cursor-pointer">
            <FileText size={14} /> PDF
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelected("pdf", f);
                e.target.value = "";
              }}
            />
          </label>
          <span className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-500 opacity-50 cursor-not-allowed">
            <PlusIcon size={14} /> More
          </span>
        </div>
      </div>

      {/* Right: Chat session panel — resizable */}
      <div
        className="hidden md:flex shrink-0 flex-col border-l border-zinc-800/60 bg-[#0f0f0f] relative overflow-visible"
        style={{ width: chatPanelWidth, minWidth: 280, maxWidth: 600 }}
      >
        {/* Resize handle */}
        <div
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize bg-zinc-700/60 hover:bg-zinc-500/80 active:bg-zinc-400/80 z-20 -translate-x-1/2"
          onMouseDown={handleChatResizeStart}
        />
        <ChatPanel recordId={recordId || undefined} />
      </div>
    </div>
  );
}

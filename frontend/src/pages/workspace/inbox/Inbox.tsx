import { useState, useEffect, useCallback, useRef } from "react";
import {
  RefreshCw,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  Star,
  Trash2,
  Clock,
  ArrowLeft,
  Search,
  Activity,
  AlertTriangle,
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
import { Dashboard } from "../Dashboard";
import { getInsights } from "../../../lib/services/insights";
import { getSnapshot } from "../../../lib/services/snapshot";
import type { BusinessInsight } from "../../../lib/workspace/dashboard-types";
import { useBusinessStore } from "../../../store/business";
import { useWorkspaceStore } from "../../../store/workspace";
import * as recordsApi from "../../../lib/services/records";
import { useSocketEvent } from "../../../lib/ws";
import { toast } from "sonner";
import type { InboxTab, InboxMessage } from "./types";
import { TABS } from "./types";
import {
  areaToSender,
  areaToColor,
  formatDate,
  formatRelativeTime,
} from "./helpers";

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

// --- Message Detail View ---

function MessageDetail({
  message,
  onBack,
  currentIndex,
  totalMessages,
  onPrev,
  onNext,
}: {
  message: InboxMessage;
  onBack: () => void;
  currentIndex: number;
  totalMessages: number;
  onPrev: () => void;
  onNext: () => void;
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

  useSocketEvent(
    "record_processing_status",
    (data: any) => {
      if (data?.record_id === recordId && data?.status === "completed") {
        if (data?.summary) {
          setInsight(data.summary);
        }
        if (data?.suggested_questions?.length) {
          setSuggestedQuestions(data.suggested_questions);
        } else if (data?.suggestions?.length) {
          setSuggestedQuestions(data.suggestions);
        }
        setLoadingInsight(false);
      }
    },
    [recordId],
  );

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
                  if (found.status === "failed") {
                    setContents((prev) =>
                      prev.map((p) =>
                        p.id === c.id ? { ...found, _processing: false } : p,
                      ),
                    );
                  } else {
                    setContents((prev) =>
                      prev.map((p) =>
                        p.id === c.id ? { ...found, _processing: false } : p,
                      ),
                    );
                  }
                }
              } catch {
                /* retry */
              }
            }, 4000);
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
              if (found.status === "failed") {
                setContents((prev) =>
                  prev.map((c) =>
                    c.id === contentId ? { ...c, _processing: false } : c,
                  ),
                );
              } else {
                setContents((prev) =>
                  prev.map((c) =>
                    c.id === contentId ? { ...found, _processing: false } : c,
                  ),
                );
              }
            }
          } catch {
            /* retry */
          }
        }, 4000);
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
            if (found.status === "failed") {
              setContents((prev) =>
                prev.map((c) =>
                  c.id === contentId ? { ...c, _processing: false } : c,
                ),
              );
            } else {
              setContents((prev) =>
                prev.map((c) =>
                  c.id === contentId ? { ...found, _processing: false } : c,
                ),
              );
            }
          }
        } catch {
          /* retry */
        }
      }, 4000);
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
                          .setPendingChatMessage(
                            "List the key points and important information?",
                          );
                      }}
                      className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[9px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                    >
                      <Sparkles size={8} />
                      <span>Ask Tendo</span>
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
                          .setPendingChatMessage(
                            "List the key points and important information?",
                          );
                      }}
                      className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[9px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                    >
                      <Sparkles size={8} />
                      <span>Ask Tendo</span>
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
                        .setPendingChatMessage(
                          "List the key points and important information?",
                        );
                    }}
                    className="flex items-center gap-1 rounded-full px-2 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[9px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                  >
                    <Sparkles size={8} />
                    <span>Ask Tendo</span>
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
                defaultOpen={idx === 0}
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
                    {content.content &&
                      !content.content.startsWith("data:") && (
                        <div className="text-[13px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                          {content.content}
                        </div>
                      )}
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
                    {content.content &&
                      !content.content.startsWith("data:") && (
                        <div className="text-[13px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                          {content.content}
                        </div>
                      )}
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
                    {content.content &&
                      !content.content.startsWith("data:") && (
                        <div className="text-[13px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                          {content.content}
                        </div>
                      )}
                  </div>
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

// --- Main Component ---

export function Inbox() {
  const [activeTab, setActiveTab] = useState<InboxTab>("primary");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [starredIds, setStarredIds] = useState<Set<string>>(new Set());
  const [openMessage, setOpenMessage] = useState<InboxMessage | null>(null);
  const [liveInsights, setLiveInsights] = useState<InboxMessage[]>([]);
  const [attentionItems, setAttentionItems] = useState<InboxMessage[]>([]);
  const [recommendationItems, setRecommendationItems] = useState<
    InboxMessage[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [recordsOffset, setRecordsOffset] = useState(0);
  const [recordsTotal, setRecordsTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const { currentProfile } = useBusinessStore();

  const PAGE_SIZE = 20;

  // Load more records (for pagination when user navigates beyond loaded set)
  const loadMoreRecords = useCallback(async () => {
    if (loadingMore) return;
    if (recordsOffset >= recordsTotal && recordsTotal > 0) return;
    setLoadingMore(true);
    try {
      const { records, count, total } = await recordsApi.getRecentRecords(
        PAGE_SIZE,
        recordsOffset,
      );
      setRecordsTotal(total);
      setUnreadCount(count);
      const newMsgs: InboxMessage[] = records.map((rec: any) => {
        const content = rec.content || "";
        const title = rec.content_title || "";
        const sender =
          title || content.slice(0, 60) || rec.title || "No content";
        const preview = content ? content.slice(0, 100) : "...";
        return {
          id: `record-${rec.record_id}`,
          sender,
          senderEmail: "",
          recipient: "",
          subject: "",
          preview,
          body: content,
          date: formatDate(rec.created_at),
          fullDate: new Date(rec.created_at).toLocaleString(),
          read: rec.is_read ?? true,
          starred: false,
          tab: "primary" as InboxTab,
          avatarColor: "bg-zinc-600",
        };
      });
      setLiveInsights((prev) => {
        const existingIds = new Set(prev.map((m) => m.id));
        const unique = newMsgs.filter((m) => !existingIds.has(m.id));
        return [...prev, ...unique];
      });
      setRecordsOffset((prev) => prev + records.length);
    } catch {
      // ignore
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, recordsOffset, recordsTotal]);

  // Initial fetch of records (first page)
  useEffect(() => {
    if (!currentProfile?.id) return;
    const fetchRecent = () => {
      recordsApi
        .getRecentRecords(PAGE_SIZE, 0)
        .then((r) => {
          setUnreadCount(r.count);
          setRecordsTotal(r.total);
          setRecordsOffset(r.records.length);
          // Merge recent record content into the engagement list
          const recentMsgs: InboxMessage[] = r.records.map((rec: any) => {
            const content = rec.content || "";
            const title = rec.content_title || "";
            const sender =
              title || content.slice(0, 60) || rec.title || "No content";
            const preview = content ? content.slice(0, 100) : "...";
            return {
              id: `record-${rec.record_id}`,
              sender,
              senderEmail: "",
              recipient: "",
              subject: "",
              preview,
              body: content,
              date: formatDate(rec.created_at),
              fullDate: new Date(rec.created_at).toLocaleString(),
              read: rec.is_read ?? true,
              starred: false,
              tab: "primary" as InboxTab,
              avatarColor: "bg-zinc-600",
            };
          });
          setLiveInsights((prev) => {
            const existingIds = new Set(recentMsgs.map((m) => m.id));
            // Deduplicate recentMsgs by id (same record_id = same id)
            const uniqueRecent = recentMsgs.filter(
              (m, i, arr) => arr.findIndex((x) => x.id === m.id) === i,
            );
            const rest = prev.filter((m) => !existingIds.has(m.id));
            return [...uniqueRecent, ...rest];
          });
        })
        .catch(() => {});
    };
    fetchRecent();
    const interval = setInterval(fetchRecent, 15000);
    return () => clearInterval(interval);
  }, [currentProfile?.id]);

  // Listen for open-record-detail events (from sidebar add button or floating panel link)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id) {
        const msg: InboxMessage = {
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
        };
        setActiveTab("primary");
        setOpenMessage(msg);
      }
    };
    window.addEventListener("tendo:open-record-detail", handler);
    return () =>
      window.removeEventListener("tendo:open-record-detail", handler);
  }, []);

  // Fetch records, insights, and recommendations
  const refreshInbox = useCallback(() => {
    if (!currentProfile?.id) return;
    setLoading(true);
    const businessId = currentProfile.id;

    Promise.all([
      getInsights(businessId, 20).catch(() => [] as BusinessInsight[]),
      getSnapshot(businessId).catch(() => null),
    ])
      .then(async ([insights, snapshot]) => {
        const insightMessages: InboxMessage[] = insights.map((ins, i) => ({
          id: `live-${ins.id || i}`,
          sender: areaToSender(ins.area),
          senderEmail: `${ins.area}@tendo.ai`,
          recipient: "",
          subject:
            ins.insight.slice(0, 80) + (ins.insight.length > 80 ? "..." : ""),
          preview: ins.insight,
          body: ins.insight,
          date: formatDate(ins.created_at),
          fullDate: new Date(ins.created_at).toLocaleString(),
          read: ins.importance < 0.8,
          starred: ins.importance >= 0.9,
          tab: "primary" as InboxTab,
          avatarColor: areaToColor(ins.area),
        }));

        setLiveInsights((prev) => {
          // Keep records from polling, add insights
          const recordItems = prev.filter((m) => m.id.startsWith("record-"));
          return [...recordItems, ...insightMessages];
        });

        // Map snapshot recommendations to attention + recommendations tabs
        if (snapshot?.recommendations) {
          const high: InboxMessage[] = [];
          const medium: InboxMessage[] = [];

          snapshot.recommendations.forEach((rec, i) => {
            const msg: InboxMessage = {
              id: `rec-${i}`,
              sender: "Tendo AI",
              senderEmail: "",
              recipient: "",
              subject: rec.action,
              preview: rec.reason,
              body: `${rec.action}\n\n${rec.reason}`,
              date: "Today",
              fullDate: new Date().toLocaleString(),
              read: rec.priority !== "high",
              starred: rec.priority === "high",
              tab:
                rec.priority === "high"
                  ? ("attention" as InboxTab)
                  : ("recommendations" as InboxTab),
              avatarColor:
                rec.priority === "high" ? "bg-red-600" : "bg-amber-600",
            };

            if (rec.priority === "high") {
              high.push(msg);
            } else {
              medium.push(msg);
            }
          });

          setAttentionItems(high);
          setRecommendationItems(medium);
        }
      })
      .finally(() => setLoading(false));
  }, [currentProfile?.id]);

  // Fetch on mount
  useEffect(() => {
    refreshInbox();
  }, [refreshInbox]);

  // Listen for new record creation to refresh
  useEffect(() => {
    const handleNewRecord = () => {
      if (currentProfile?.id) {
        recordsApi
          .getAllRecords()
          .then((records) => {
            // Preserve read state from current list for existing records
            const currentReadState = new Map<string, boolean>();
            liveInsights.forEach((m) => {
              if (m.id.startsWith("record-")) {
                currentReadState.set(m.id, m.read);
              }
            });

            const allRecords: InboxMessage[] = records.map((rec: any) => {
              const msgId = `record-${rec.id}`;
              // Use current UI read state if available, otherwise use API value
              const isRead = currentReadState.has(msgId)
                ? currentReadState.get(msgId)!
                : (rec.is_read ?? false);
              return {
                id: msgId,
                sender: rec.title || "Untitled",
                senderEmail: "",
                recipient: "",
                subject: rec.first_content
                  ? rec.first_content.slice(0, 80) +
                    (rec.first_content.length > 80 ? "..." : "")
                  : rec.title || "Untitled",
                preview: rec.first_content || "No content yet",
                body: rec.first_content || "",
                date: formatDate(rec.updated_at || rec.created_at),
                fullDate: new Date(
                  rec.updated_at || rec.created_at,
                ).toLocaleString(),
                read: isRead,
                starred: false,
                tab: "primary" as InboxTab,
                avatarColor: "bg-zinc-600",
              };
            });
            setLiveInsights((prev) => {
              const nonRecords = prev.filter(
                (m) => !m.id.startsWith("record-"),
              );
              return [...allRecords, ...nonRecords];
            });
          })
          .catch(() => {});
      }
    };
    window.addEventListener("tendo:open-new-record", handleNewRecord);
    return () =>
      window.removeEventListener("tendo:open-new-record", handleNewRecord);
  }, [currentProfile?.id, liveInsights]);

  // Listen for record_updated to show content after processing
  useSocketEvent(
    "record_updated",
    (data: any) => {
      if (data?.business_id !== currentProfile?.id) return;
      const rid = `record-${data.id}`;
      setLiveInsights((prev) =>
        prev.map((m) => {
          if (m.id !== rid) return m;
          const preview = data.first_content || m.preview;
          return {
            ...m,
            sender: data.title || m.sender,
            subject: preview ? preview.slice(0, 80) : m.subject,
            preview: preview || m.preview,
            body: preview || m.body,
          };
        }),
      );
    },
    [currentProfile?.id],
  );

  // Determine which messages to show based on tab
  const getMessages = (): InboxMessage[] => {
    switch (activeTab) {
      case "primary":
        return liveInsights;
      case "attention":
        return attentionItems;
      case "recommendations":
        return recommendationItems;
      default:
        return [];
    }
  };

  const filteredMessages = getMessages();

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredMessages.slice(0, 25).map((m) => m.id)));
    }
  };

  const deleteSelected = async () => {
    const recordIds = [...selectedIds]
      .filter((id) => id.startsWith("record-"))
      .map((id) => id.replace("record-", ""));
    if (!recordIds.length) return;
    setDeleting(true);

    // Delete in batches of 20
    for (let i = 0; i < recordIds.length; i += 20) {
      const batch = recordIds.slice(i, i + 20);
      await Promise.all(
        batch.map((rid) => recordsApi.deleteRecord(rid).catch(() => {})),
      );
    }

    setLiveInsights((prev) => prev.filter((m) => !selectedIds.has(m.id)));
    setSelectedIds(new Set());
    setDeleting(false);
    refreshInbox();
  };

  const deleteSingle = async (msgId: string) => {
    const rid = msgId.startsWith("record-") ? msgId.replace("record-", "") : "";
    if (!rid) return;
    setDeleting(true);
    try {
      await recordsApi.deleteRecord(rid);
      setLiveInsights((prev) => prev.filter((m) => m.id !== msgId));
    } catch (e) {
      console.error("Delete failed:", e);
    }
    setDeleting(false);
  };

  const toggleStar = (id: string) => {
    setStarredIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // If a message is open, show detail view
  if (openMessage) {
    const currentIndex = filteredMessages.findIndex(
      (m) => m.id === openMessage.id,
    );
    const totalMessages = filteredMessages.length;
    const hasMoreToLoad = recordsOffset < recordsTotal;

    return (
      <MessageDetail
        message={openMessage}
        onBack={() => setOpenMessage(null)}
        currentIndex={currentIndex >= 0 ? currentIndex : 0}
        totalMessages={hasMoreToLoad ? recordsTotal : totalMessages}
        onPrev={() => {
          if (currentIndex > 0) {
            setOpenMessage(filteredMessages[currentIndex - 1]);
          }
        }}
        onNext={async () => {
          if (currentIndex < totalMessages - 1) {
            setOpenMessage(filteredMessages[currentIndex + 1]);
          } else if (hasMoreToLoad) {
            await loadMoreRecords();
          }
        }}
      />
    );
  }

  return (
    <div className="flex h-full flex-col bg-[#0a0a0a]">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-zinc-800/60 px-4 py-2">
        <button
          type="button"
          onClick={toggleSelectAll}
          className={clsx(
            "flex h-4 w-4 items-center justify-center rounded border transition-colors",
            selectedIds.size > 0
              ? "border-emerald-500 bg-emerald-500"
              : "border-zinc-600 hover:border-zinc-500",
          )}
          aria-label="Select all"
        >
          {selectedIds.size > 0 &&
            selectedIds.size === filteredMessages.length && (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path
                  d="M2 5l2.5 2.5L8 3"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          {selectedIds.size > 0 &&
            selectedIds.size < filteredMessages.length && (
              <span className="h-0.5 w-2.5 bg-white" />
            )}
        </button>
        {selectedIds.size > 0 && (
          <button
            type="button"
            onClick={deleteSelected}
            disabled={deleting}
            className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200 disabled:opacity-50"
            aria-label="Delete selected"
          >
            {deleting ? (
              <RefreshCw size={16} className="animate-spin" />
            ) : (
              <Trash2 size={16} />
            )}
          </button>
        )}
        <button
          type="button"
          onClick={refreshInbox}
          className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200"
          aria-label="Refresh"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>

        {/* Search bar */}
        <div className="flex-1">
          <div className="relative w-full max-w-[440px]">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500"
            />
            <input
              type="text"
              placeholder="Search..."
              className="w-full rounded-md border border-zinc-800 bg-zinc-900/50 py-1 pl-8 pr-8 text-[12px] text-zinc-300 placeholder-zinc-500 transition-colors focus:border-zinc-700 focus:outline-none"
            />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden rounded border border-zinc-700/60 bg-zinc-800/50 px-1 py-0.5 text-[9px] font-medium text-zinc-500 sm:inline">
              ⌘K
            </kbd>
          </div>
        </div>

        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200"
          aria-label="More actions"
        >
          <MoreVertical size={16} />
        </button>
        <span className="text-[12px] text-zinc-500">
          1–{filteredMessages.length} of {filteredMessages.length}
        </span>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
          aria-label="Previous page"
        >
          <ChevronLeft size={16} />
        </button>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
          aria-label="Next page"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Category tabs */}
      <div className="flex items-center border-b border-zinc-800/60">
        {TABS.map((tab) => {
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "relative flex flex-1 items-center justify-center gap-1.5 px-4 py-3 text-[13px] font-medium transition-colors",
                activeTab === tab.id
                  ? "text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.02]",
              )}
            >
              {tab.label}
              {tab.id === "primary" && unreadCount > 0 && (
                <span className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold bg-blue-500/20 text-blue-400">
                  {unreadCount}
                </span>
              )}
              {tab.id !== "primary" && tab.badge && (
                <span
                  className={clsx(
                    "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                    tab.badgeColor || "bg-emerald-500/20 text-emerald-400",
                  )}
                >
                  {tab.badge} new
                </span>
              )}
              {activeTab === tab.id && (
                <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-zinc-400" />
              )}
            </button>
          );
        })}
      </div>

      {/* Content area — show Dashboard for insights tab, message list for others */}
      {activeTab === "insights" ? (
        <div className="flex-1 overflow-y-auto">
          <Dashboard />
        </div>
      ) : loading ? (
        <div className="flex-1 overflow-y-auto">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-3 border-b border-zinc-800/40 px-4 py-3 animate-pulse"
            >
              <div className="h-4 w-4 rounded bg-zinc-800" />
              <div className="h-4 w-4 rounded bg-zinc-800" />
              <div className="h-3 w-[120px] rounded bg-zinc-800" />
              <div className="flex-1 flex gap-2">
                <div className="h-3 w-[180px] rounded bg-zinc-800" />
                <div className="h-3 w-[100px] rounded bg-zinc-800/60" />
              </div>
              <div className="h-3 w-[50px] rounded bg-zinc-800" />
            </div>
          ))}
        </div>
      ) : filteredMessages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center px-6">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800/60">
              {activeTab === "primary" && (
                <Activity size={22} className="text-zinc-500" />
              )}
              {activeTab === "attention" && (
                <AlertTriangle size={22} className="text-red-400" />
              )}
              {activeTab === "recommendations" && (
                <Sparkles size={22} className="text-amber-400" />
              )}
            </div>
            <p className="text-[14px] font-medium text-zinc-300">
              {activeTab === "primary" && "No activities yet"}
              {activeTab === "attention" && "Nothing needs attention"}
              {activeTab === "recommendations" && "No recommendations yet"}
            </p>
            <p className="mt-1 text-[12px] text-zinc-500">
              {activeTab === "primary" &&
                "Business activities and records will appear here as you interact with Tendo."}
              {activeTab === "attention" &&
                "High priority items that require your action will show up here."}
              {activeTab === "recommendations" &&
                "Suggestions to improve your business will appear here."}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {filteredMessages.map((msg) => (
            <div
              key={msg.id}
              onClick={() => {
                setOpenMessage(msg);
                const rid = msg.id.startsWith("record-")
                  ? msg.id.replace("record-", "")
                  : "";
                if (rid) {
                  recordsApi.markRecordRead(rid).catch(() => {});
                  setUnreadCount((c) => Math.max(0, c - 1));
                  setLiveInsights((prev) =>
                    prev.map((m) =>
                      m.id === msg.id ? { ...m, read: true } : m,
                    ),
                  );
                }
              }}
              className={clsx(
                "group flex items-center gap-0 border-b border-zinc-800/40 px-4 py-1.5 transition-colors cursor-pointer",
                !msg.read ? "bg-zinc-900/50" : "bg-transparent",
                selectedIds.has(msg.id) && "bg-emerald-500/5",
                "hover:bg-white/[0.03] hover:shadow-[inset_2px_0_0_0_#3ecf8e]",
              )}
            >
              {/* Checkbox */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleSelect(msg.id);
                }}
                className={clsx(
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors mr-2",
                  selectedIds.has(msg.id)
                    ? "border-emerald-500 bg-emerald-500"
                    : "border-zinc-700 hover:border-zinc-500",
                )}
                aria-label={`Select message from ${msg.sender}`}
              >
                {selectedIds.has(msg.id) && (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M2 5l2.5 2.5L8 3"
                      stroke="white"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </button>

              {/* Star */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleStar(msg.id);
                }}
                className={clsx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors mr-2",
                  starredIds.has(msg.id)
                    ? "text-yellow-400"
                    : "text-zinc-600 hover:text-zinc-400",
                )}
                aria-label={starredIds.has(msg.id) ? "Unstar" : "Star"}
              >
                <Star
                  size={16}
                  fill={starredIds.has(msg.id) ? "currentColor" : "none"}
                />
              </button>

              {/* Sender */}
              <span
                className={clsx(
                  "w-[160px] shrink-0 truncate text-[13px]",
                  !msg.read ? "font-medium text-zinc-100" : "text-zinc-400",
                )}
              >
                {msg.sender}
              </span>

              {/* Subject + preview */}
              <div className="min-w-0 flex-1 flex items-baseline gap-1 mr-3">
                <span
                  className={clsx(
                    "shrink-0 truncate text-[13px]",
                    !msg.read ? "text-zinc-100" : "text-zinc-400",
                  )}
                >
                  {msg.subject}
                </span>
                {msg.subject && (
                  <span className="text-zinc-600 text-[13px] shrink-0">-</span>
                )}
                <span className="min-w-0 truncate text-[13px] text-zinc-500">
                  {msg.preview}
                </span>
              </div>

              {/* Hover actions */}
              <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex mr-2">
                <button
                  type="button"
                  className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
                  aria-label="Delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSingle(msg.id);
                  }}
                >
                  <Trash2 size={15} />
                </button>
                <button
                  type="button"
                  className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
                  aria-label="Snooze"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Clock size={15} />
                </button>
              </div>

              {/* Date */}
              <span
                className={clsx(
                  "shrink-0 text-[12px] tabular-nums",
                  !msg.read ? "text-zinc-200" : "text-zinc-500",
                )}
              >
                {msg.date}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

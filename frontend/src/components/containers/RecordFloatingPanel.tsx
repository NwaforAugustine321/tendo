import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import {
  Type,
  Image,
  Mic,
  FileText,
  X,
  Sparkles,
  Lightbulb,
  ChevronDown,
  Plus,
  ExternalLink,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";
import { FloatingPanel } from "./FloatingPanel";
import { useWorkspaceStore } from "../../store/workspace";
import { useBusinessStore } from "../../store/business";
import { useSocketEvent } from "../../lib/ws";
import type { Record } from "../../lib/workspace/types";
import * as recordsApi from "../../lib/services/records";

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// --- Collapsible Section (same as detail page) ---

function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = false,
  icon,
  processing,
  children,
}: {
  title: string;
  subtitle: string;
  defaultOpen?: boolean;
  icon?: string;
  processing?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const renderIcon = () => {
    if (processing)
      return (
        <div className="h-3 w-3 animate-spin rounded-full border-2 border-zinc-600 border-t-emerald-500" />
      );
    switch (icon) {
      case "text":
        return <Type size={12} className="text-zinc-400" />;
      case "image":
        return <Image size={12} className="text-zinc-400" />;
      case "audio":
        return <Mic size={12} className="text-zinc-400" />;
      case "pdf":
        return <FileText size={12} className="text-zinc-400" />;
      default:
        return <Type size={12} className="text-zinc-400" />;
    }
  };

  return (
    <div className="mb-2 bg-zinc-900/20 rounded-lg border border-zinc-800/20">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <span className="shrink-0">{renderIcon()}</span>
        <div className="min-w-0 flex-1">
          <span className="text-[11px] font-medium text-zinc-200 line-clamp-1">
            {title}
          </span>
          {processing && (
            <span className="text-[10px] text-zinc-500 ml-2">
              Processing...
            </span>
          )}
        </div>
        {!processing && (
          <span className="text-[10px] text-zinc-500 shrink-0 mr-1">
            {subtitle}
          </span>
        )}
        <ChevronDown
          size={14}
          className={clsx(
            "text-zinc-500 transition-transform shrink-0",
            !open && "-rotate-90",
          )}
        />
      </button>
      {open && <div className="px-3 pb-3 pt-0">{children}</div>}
    </div>
  );
}

// --- Content Tab (same logic as detail page) ---

function RecordContentTab({
  recordId,
  onOpenDetail,
}: {
  recordId: string;
  onOpenDetail: (msg: string) => void;
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
  const [insight, setInsight] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [loadingInsight, setLoadingInsight] = useState(true);
  const [insightExpanded, setInsightExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

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

  // Fetch all record contents on mount
  // Auto-scroll to bottom when new content is added
  useEffect(() => {
    if (scrollRef.current && contents.length > 0) {
      setTimeout(() => {
        scrollRef.current?.scrollTo({
          top: scrollRef.current.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    }
  }, [contents.length]);

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
        // Resume polling for any content still processing
        data.forEach((c: any) => {
          if (c.status === "processing" && c.id) {
            const pollInterval = setInterval(async () => {
              try {
                const updated = await recordsApi.getRecordContents(recordId);
                const found = updated.find((u: any) => u.id === c.id);
                if (found && found.status !== "processing") {
                  clearInterval(pollInterval);
                  setContents((prev) =>
                    prev.map((p) =>
                      p.id === c.id ? { ...found, _processing: false } : p,
                    ),
                  );
                }
              } catch {
                /* retry */
              }
            }, 4000);
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
  };

  const handleFileSelected = useCallback(
    async (type: string, file: File) => {
      const fileName = file.name || `${type} file`;
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
                setContents((prev) =>
                  prev.map((c) =>
                    c.id === contentId ? { ...found, _processing: false } : c,
                  ),
                );
              }
            } catch {
              /* retry */
            }
          }, 4000);
        } catch {
          setContents((prev) => prev.filter((c) => c.id !== tempId));
          toast.error("Failed to upload file");
        } finally {
          setSaving(false);
        }
      };
      reader.readAsDataURL(file);
    },
    [recordId],
  );

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
            setContents((prev) =>
              prev.map((c) =>
                c.id === contentId ? { ...found, _processing: false } : c,
              ),
            );
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
    <div className="flex flex-col h-full overflow-hidden">
      {/* Scrollable content area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3">
        <div className="flex gap-3">
          {/* Main content column */}
          <div className="flex-1">
            {/* Loading skeleton */}
            {loadingContent && (
              <div className="space-y-2 animate-pulse">
                <div className="rounded-lg border border-zinc-800/20 bg-zinc-900/30 p-3">
                  <div className="flex items-center gap-1.5 mb-2">
                    <div className="h-3 w-3 rounded bg-zinc-700" />
                    <div className="h-2 w-10 rounded bg-zinc-700" />
                  </div>
                  <div className="space-y-1.5">
                    <div className="h-2.5 w-full rounded bg-zinc-800" />
                    <div className="h-2.5 w-3/4 rounded bg-zinc-800" />
                  </div>
                </div>
                <div className="rounded-lg border border-zinc-800/20 bg-zinc-900/30 p-3">
                  <div className="flex items-center gap-1.5 mb-2">
                    <div className="h-3 w-3 rounded bg-zinc-700" />
                    <div className="h-2 w-10 rounded bg-zinc-700" />
                  </div>
                  <div className="space-y-1.5">
                    <div className="h-2.5 w-full rounded bg-zinc-800" />
                    <div className="h-2.5 w-1/2 rounded bg-zinc-800" />
                  </div>
                </div>
              </div>
            )}

            {/* Empty state */}
            {!loadingContent && contents.length === 0 && !addingType && (
              <div className="py-8 text-center text-[11px] text-zinc-500">
                No content yet. Add some below.
              </div>
            )}

            {/* Content list as collapsible sections */}
            {contents.map((content, idx) => (
              <CollapsibleSection
                key={content.id}
                title={
                  content._processing
                    ? content._fileName || "Processing..."
                    : content.content_type === "text"
                      ? content.content.slice(0, 50) +
                        (content.content.length > 50 ? "..." : "")
                      : content.content &&
                          !content.content.startsWith("data:") &&
                          !content.content.startsWith("[Processing")
                        ? content.content.slice(0, 50) +
                          (content.content.length > 50 ? "..." : "")
                        : content._fileName ||
                          content.content_type.charAt(0).toUpperCase() +
                            content.content_type.slice(1)
                }
                subtitle={
                  content._processing
                    ? ""
                    : formatRelativeTime(content.created_at)
                }
                defaultOpen={idx === 0}
                icon={content.content_type}
                processing={content._processing}
              >
                {content.content_type === "image" &&
                (content.file_url ||
                  content.content.startsWith("data:image")) ? (
                  <div className="flex items-start gap-2">
                    <a
                      href={content.file_url || content.content}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0"
                    >
                      <img
                        src={content.file_url || content.content}
                        alt="Uploaded image"
                        className="max-w-[120px] max-h-[80px] rounded-md cursor-pointer hover:opacity-80 transition-opacity"
                      />
                    </a>
                    {content.content &&
                      !content.content.startsWith("data:") && (
                        <div className="text-[11px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                          {content.content}
                        </div>
                      )}
                  </div>
                ) : content.content_type === "audio" &&
                  (content.file_url ||
                    content.content.startsWith("data:audio")) ? (
                  <div className="flex flex-col gap-2">
                    <audio
                      controls
                      src={content.file_url || content.content}
                      className="w-full max-w-[250px]"
                    />
                    {content.content &&
                      !content.content.startsWith("data:") && (
                        <div className="text-[11px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                          {content.content}
                        </div>
                      )}
                  </div>
                ) : content.content_type === "pdf" ? (
                  <div className="flex items-start gap-2">
                    {content.file_url && (
                      <a
                        href={content.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0"
                      >
                        <div className="w-[80px] h-[60px] rounded-md bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                          <FileText size={24} className="text-zinc-400" />
                        </div>
                      </a>
                    )}
                    {content.content &&
                      !content.content.startsWith("data:") && (
                        <div className="text-[11px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                          {content.content}
                        </div>
                      )}
                  </div>
                ) : (
                  <div className="text-[12px] leading-relaxed text-zinc-300 whitespace-pre-wrap">
                    {content.content}
                  </div>
                )}
              </CollapsibleSection>
            ))}

            {/* New text content input area */}
            {addingType === "text" && (
              <div className="mt-2 rounded-lg border border-zinc-800/40 bg-zinc-900/30 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] uppercase tracking-wide text-zinc-500">
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
                  className="w-full min-h-[80px] resize-none bg-transparent text-[12px] leading-relaxed text-zinc-200 placeholder-zinc-600 focus:outline-none"
                />
                <div className="flex items-center gap-2 mt-2">
                  <button
                    type="button"
                    onClick={handleSaveContent}
                    disabled={!newContent.trim() || saving}
                    className="rounded-md bg-emerald-600 px-2.5 py-1 text-[10px] font-medium text-white hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAddingType(null);
                      setNewContent("");
                    }}
                    className="rounded-md px-2.5 py-1 text-[10px] font-medium text-zinc-400 hover:text-zinc-200"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Insight panel — right column */}
          <div className="w-[180px] shrink-0 sticky top-0 self-start">
            <div className="rounded-lg border border-zinc-800/40 bg-[#141414] p-2.5">
              {loadingInsight ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={10} className="text-emerald-500" />
                    <span className="text-[9px] font-medium text-zinc-400">
                      Overview
                    </span>
                  </div>
                  <div className="animate-pulse space-y-1.5">
                    <div className="h-2 w-full rounded bg-zinc-800" />
                    <div className="h-2 w-4/5 rounded bg-zinc-800" />
                    <div className="h-2 w-3/5 rounded bg-zinc-800" />
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      onOpenDetail(
                        "List the key points and important information?",
                      )
                    }
                    className="flex items-center gap-1 rounded-full px-1.5 py-0.5 mt-2 border border-emerald-500/30 bg-emerald-500/5 text-[8px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                  >
                    <Sparkles size={7} />
                    <span>Ask Tendo</span>
                  </button>
                </div>
              ) : insight ? (
                <>
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Sparkles size={10} className="text-emerald-500" />
                    <span className="text-[9px] font-medium text-zinc-400">
                      Overview
                    </span>
                  </div>
                  <div
                    className={clsx(
                      "overflow-hidden transition-all duration-200",
                      insightExpanded
                        ? "max-h-[250px] overflow-y-auto"
                        : "max-h-[70px]",
                    )}
                  >
                    <p className="text-[10px] leading-relaxed text-zinc-300">
                      {insight}
                    </p>
                  </div>
                  {insight.length > 100 && (
                    <button
                      type="button"
                      onClick={() => setInsightExpanded(!insightExpanded)}
                      className="mt-1 text-[9px] text-[#3ecf8e] hover:text-[#3ecf8e]/80 transition-colors"
                    >
                      {insightExpanded ? "See less" : "See more"}
                    </button>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {suggestedQuestions.map((q, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => onOpenDetail(q)}
                        className="flex items-center gap-1 rounded-full px-1.5 py-0.5 border border-zinc-700/50 bg-[#1a1a1a] text-[8px] text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
                      >
                        <Lightbulb
                          size={7}
                          className="text-[#3ecf8e] shrink-0"
                        />
                        <span className="line-clamp-1">{q}</span>
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={() =>
                        onOpenDetail(
                          "List the key points and important information?",
                        )
                      }
                      className="flex items-center gap-1 rounded-full px-1.5 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[8px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                    >
                      <Sparkles size={7} />
                      <span>Ask Tendo</span>
                    </button>
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={10} className="text-emerald-500" />
                    <span className="text-[9px] text-zinc-500">
                      No insights yet
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      onOpenDetail(
                        "List the key points and important information?",
                      )
                    }
                    className="flex items-center gap-1 rounded-full px-1.5 py-0.5 border border-emerald-500/30 bg-emerald-500/5 text-[8px] text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-colors"
                  >
                    <Sparkles size={7} />
                    <span>Ask Tendo</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Fixed bottom — source input buttons */}
      <div className="shrink-0 flex items-center gap-1.5 px-3 py-2 border-t border-zinc-800/40 flex-wrap">
        <button
          type="button"
          onClick={() => handleAddContent("text")}
          className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-600 text-[10px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200"
        >
          <Type size={11} /> Text
        </button>
        <label className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-600 text-[10px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200 cursor-pointer">
          <Image size={11} /> Image
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
        <label className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-600 text-[10px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200 cursor-pointer">
          <Mic size={11} /> Audio
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
        <label className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-600 text-[10px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200 cursor-pointer">
          <FileText size={11} /> PDF
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
        <span className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-600 text-[10px] text-zinc-500 opacity-50 cursor-not-allowed">
          <Plus size={11} /> More
        </span>
      </div>
    </div>
  );
}

// --- Main Export ---

export function RecordFloatingPanel() {
  const { openRecordIds } = useWorkspaceStore();

  if (openRecordIds.length === 0) return null;

  return (
    <>
      {openRecordIds.map((recordId, index) => (
        <SingleRecordPanel key={recordId} recordId={recordId} index={index} />
      ))}
    </>
  );
}

function SingleRecordPanel({
  recordId,
  index,
}: {
  recordId: string;
  index: number;
}) {
  const { records } = useWorkspaceStore();

  const activeRecord: Record | null = useMemo(() => {
    for (const [, folderRecords] of records) {
      const found = folderRecords.find((r) => r.id === recordId);
      if (found) return found;
    }
    return null;
  }, [recordId, records]);

  const title = activeRecord?.title || "Untitled";

  const handleOpenDetail = (chatMessage?: string) => {
    // Close the floating panel and navigate to the record detail page
    useWorkspaceStore.getState().closeRecord(recordId);
    if (chatMessage) {
      useWorkspaceStore.getState().setPendingChatMessage(chatMessage);
    }
    window.dispatchEvent(
      new CustomEvent("tendo:open-record-detail", {
        detail: {
          id: recordId,
          title,
          created_at: activeRecord?.createdAt || "",
        },
      }),
    );
  };

  const titleElement = (
    <span className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          handleOpenDetail();
        }}
        className="truncate max-w-[180px] hover:text-emerald-400 transition-colors"
        title="Open in full view"
      >
        {title}
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          handleOpenDetail();
        }}
        className="flex items-center text-emerald-400 hover:text-emerald-300 transition-colors"
        title="Open in full view"
      >
        <ExternalLink size={10} />
      </button>
    </span>
  );

  return (
    <FloatingPanel
      visible={true}
      title={titleElement}
      onClose={() => useWorkspaceStore.getState().closeRecord(recordId)}
      defaultWidth={700}
      defaultHeight={480}
      offsetIndex={index}
    >
      <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
        <RecordContentTab
          recordId={recordId}
          onOpenDetail={(msg) => handleOpenDetail(msg)}
        />
      </div>
    </FloatingPanel>
  );
}

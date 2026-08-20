import { useEffect, useState, useCallback } from "react";
import { Sparkles, Lightbulb, Loader2 } from "lucide-react";
import clsx from "clsx";
import { useWorkspaceStore } from "../../store/workspace";
import { useBusinessStore } from "../../store/business";
import { useEventReceiver } from "../../hooks/useEmitReceiver";
import * as recordsApi from "../../lib/services/records";

type InsightEntry = {
  id: string;
  insight: string;
  suggested_questions: string[];
  timestamp: string;
};

const WORD_LIMIT = 25;

function truncateWords(text: string, limit: number): string {
  const words = text.split(/\s+/);
  if (words.length <= limit) return text;
  return words.slice(0, limit).join(" ") + "...";
}

function isLongText(text: string): boolean {
  return text.split(/\s+/).length > WORD_LIMIT || text.length > 400;
}

export function RecordInsightPanel() {
  const { currentProfile } = useBusinessStore();
  const businessId = currentProfile?.id || "";
  const [insights, setInsights] = useState<InsightEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!businessId) {
      setInsights([]);
      return;
    }

    setLoading(true);

    // Fetch all folders, then all records, then aggregate insights
    recordsApi
      .getFolders()
      .then(async (folders) => {
        const allInsights: InsightEntry[] = [];

        for (const folder of folders) {
          try {
            const records = await recordsApi.getRecords(folder.id);
            for (const record of records) {
              const aiInsights = record.ai_insight || [];
              for (const entry of aiInsights) {
                allInsights.push({
                  id: `${record.id}-${entry.version}`,
                  insight: entry.insight,
                  suggested_questions: entry.suggested_questions || [],
                  timestamp: entry.timestamp,
                });
              }
            }
          } catch {
            // Skip failed folders
          }
        }

        // Sort by timestamp descending (newest first)
        allInsights.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        );
        setInsights(allInsights);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [businessId]);

  // Listen for new processing completions via useEventReceiver
  const { events: documentProgressEvents } = useEventReceiver([
    "document.progress",
  ]);

  useEffect(() => {
    if (!businessId || documentProgressEvents.length === 0) return;
    const latest = documentProgressEvents[documentProgressEvents.length - 1];
    const detail = latest.data as any;
    const status = (detail?.status || "").toLowerCase();
    if (status === "completed" && detail?.data) {
      // Refresh records to get updated insights
      recordsApi
        .getRecentRecords()
        .then(({ records }) => {
          const allInsights: InsightEntry[] = [];
          for (const record of records) {
            const aiInsights = record?.ai_insight || [];
            for (const entry of aiInsights) {
              allInsights.push({
                id: `${record.id}-${entry.version}`,
                insight: entry.insight,
                suggested_questions: entry.suggested_questions || [],
                timestamp: entry.timestamp,
              });
            }
          }
          allInsights.sort(
            (a, b) =>
              new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
          );
          setInsights(allInsights);
        })
        .catch(() => {});
    }
  }, [documentProgressEvents, businessId]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading && (
          <div className="flex items-center gap-2 py-4 justify-center">
            <Loader2 size={14} className="animate-spin text-[#3ecf8e]" />
            <span className="text-xs text-zinc-500">Loading insights...</span>
          </div>
        )}

        {!loading && insights.length === 0 && (
          <div className="py-6 text-center">
            <Lightbulb size={20} className="mx-auto mb-2 text-zinc-600" />
            <p className="text-xs text-zinc-500">No insights yet</p>
            <p className="text-[10px] text-zinc-600 mt-1">
              Capture content to generate insights
            </p>
          </div>
        )}

        {insights.map((entry) => {
          const isExpanded = expandedIds.has(entry.id);
          const isLong = isLongText(entry.insight);
          const displayText =
            isExpanded || !isLong
              ? entry.insight
              : truncateWords(entry.insight, WORD_LIMIT);

          return (
            <div
              key={entry.id}
              className="rounded-lg border border-white/5 bg-[#141414] p-3"
            >
              <p className="text-xs leading-relaxed text-zinc-300 mb-1">
                {displayText}
              </p>

              {isLong && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleExpanded(entry.id);
                  }}
                  className="text-[10px] text-[#3ecf8e] hover:text-[#3ecf8e]/80 mb-2 block"
                >
                  {isExpanded ? "See less" : "See more"}
                </button>
              )}

              {entry.suggested_questions.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {entry.suggested_questions.map((q, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        useWorkspaceStore.getState().setPendingChatMessage(q);
                        useWorkspaceStore
                          .getState()
                          .setDashboardChatVisible(true);
                      }}
                      className={clsx(
                        "flex items-center gap-1 rounded-full px-2.5 py-1",
                        "border border-zinc-700/50 bg-[#1a1a1a]",
                        "text-[10px] text-zinc-400 hover:text-zinc-200 hover:border-zinc-600",
                        "transition-colors text-left",
                      )}
                    >
                      <Lightbulb
                        size={10}
                        className="text-[#3ecf8e] shrink-0"
                      />
                      <span>{q}</span>
                    </button>
                  ))}
                </div>
              )}

              <div className="mt-2 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => {
                    useWorkspaceStore.getState().setDashboardChatVisible(true);
                    useWorkspaceStore
                      .getState()
                      .setPendingChatMessage(
                        `List the key points and important information? "${entry.insight}"`,
                      );
                  }}
                  className="flex items-center gap-1 rounded-full px-2.5 py-1 border border-[#3ecf8e]/30 bg-[#3ecf8e]/5 text-[10px] text-[#3ecf8e] hover:bg-[#3ecf8e]/10 hover:border-[#3ecf8e]/50 transition-colors"
                >
                  <Sparkles size={10} />
                  <span>Ask Tendo</span>
                </button>
                <span className="text-[9px] text-zinc-600">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

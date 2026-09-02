import { useCallback, useEffect, useState } from "react";
import { getInsights } from "../../../lib/services/insights";
import * as snapsApi from "../../../lib/services/snaps";
import type { Snap } from "../../../lib/services/snaps";
import type { BusinessInsight } from "../../../lib/workspace/dashboard-types";
import * as recordsApi from "../../../lib/services/records";
import { useBusinessStore } from "../../../store/business";
import { useEventReceiver } from "../../../hooks/useEmitReceiver";
import type { InboxMessage } from "./types";
import { formatDate } from "./helpers";

const PAGE_SIZE = 20;

function recordToMessage(rec: any): InboxMessage {
  const content = rec.content || rec.first_content || "";
  const title = rec.content_title || rec.title || "";
  return {
    id: `record-${rec.record_id || rec.id}`,
    sender: title || content.slice(0, 60) || "Untitled",
    senderEmail: "",
    recipient: "",
    subject: content
      ? content.slice(0, 80) + (content.length > 80 ? "..." : "")
      : title || "Untitled",
    preview: content || "No content yet",
    body: content,
    date: formatDate(rec.updated_at || rec.created_at),
    fullDate: new Date(rec.updated_at || rec.created_at).toLocaleString(),
    read: rec.is_read ?? true,
    starred: false,
    tab: "primary",
    avatarColor: "bg-zinc-600",
  };
}

export function useHomeData() {
  const { currentProfile } = useBusinessStore();
  const [recentRecords, setRecentRecords] = useState<InboxMessage[]>([]);
  const [insights, setInsights] = useState<BusinessInsight[]>([]);
  const [attention, setAttention] = useState<Snap[]>([]);
  const [recommendations, setRecommendations] = useState<Snap[]>([]);
  const [priority, setPriority] = useState<Snap[]>([]);
  const [loading, setLoading] = useState(true);
  const [recordsOffset, setRecordsOffset] = useState(0);
  const [recordsTotal, setRecordsTotal] = useState(0);

  const refresh = useCallback(async () => {
    const businessId = currentProfile?.id;
    if (!businessId) return;

    setLoading(true);
    try {
      const [
        recordsResult,
        insightResult,
        attentionResult,
        recommendationResult,
        priorityResult,
      ] = await Promise.all([
        recordsApi
          .getRecentRecords(PAGE_SIZE, 0)
          .catch(() => ({ records: [], total: 0 })),
        getInsights(businessId, 20).catch(() => [] as BusinessInsight[]),
        snapsApi.listSnaps(businessId, "attention").catch(() => [] as Snap[]),
        snapsApi
          .listSnaps(businessId, "recommendation")
          .catch(() => [] as Snap[]),
        snapsApi.listSnaps(businessId, "priority").catch(() => [] as Snap[]),
      ]);

      const records = recordsResult.records.map(recordToMessage);
      setRecentRecords(records);
      setRecordsOffset(records.length);
      setRecordsTotal(recordsResult.total || 0);
      setInsights(insightResult);
      setAttention(attentionResult);
      setRecommendations(recommendationResult);
      setPriority(priorityResult);
    } finally {
      setLoading(false);
    }
  }, [currentProfile?.id]);

  useEffect(() => {
    if (!currentProfile?.id) return;
    void refresh();

    const interval = setInterval(() => {
      void refresh();
    }, 15000);

    return () => clearInterval(interval);
  }, [currentProfile?.id, refresh]);

  const { events: recordUpdatedEvents } = useEventReceiver(["record_updated"]);

  useEffect(() => {
    const latest = recordUpdatedEvents.at(-1);
    const data = latest?.data as any;
    if (!data || data.business_id !== currentProfile?.id) return;

    const id = `record-${data.id}`;
    setRecentRecords((prev) =>
      prev.map((record) =>
        record.id !== id
          ? record
          : {
              ...record,
              sender: data.title || record.sender,
              subject: data.first_content
                ? data.first_content.slice(0, 80) +
                  (data.first_content.length > 80 ? "..." : "")
                : record.subject,
              preview: data.first_content || record.preview,
              body: data.first_content || record.body,
            },
      ),
    );
  }, [recordUpdatedEvents, currentProfile?.id]);

  useEffect(() => {
    const handleNewRecord = () => void refresh();
    window.addEventListener("tendo:open-new-record", handleNewRecord);
    return () =>
      window.removeEventListener("tendo:open-new-record", handleNewRecord);
  }, [refresh]);

  const loadMoreRecords = useCallback(async () => {
    if (recordsOffset >= recordsTotal) return;

    const result = await recordsApi.getRecentRecords(PAGE_SIZE, recordsOffset);
    const messages = result.records.map(recordToMessage);

    setRecentRecords((prev) => {
      const ids = new Set(prev.map((item) => item.id));
      return [...prev, ...messages.filter((item) => !ids.has(item.id))];
    });
    setRecordsOffset((offset) => offset + result.records.length);
    setRecordsTotal(result.total || recordsTotal);
  }, [recordsOffset, recordsTotal]);

  const actOnSnap = useCallback(
    async (snap: Snap, action: "save" | "complete") => {
      const businessId = currentProfile?.id;
      if (!businessId) return;

      const remove = (items: Snap[]) =>
        items.filter((item) => item.snap_id !== snap.snap_id);

      if (action === "save") {
        const saved = await snapsApi.saveSnap(businessId, snap.snap_id);
        setAttention(remove);
        setRecommendations(remove);
        setPriority((prev) => [saved, ...remove(prev)]);
        return;
      }

      await snapsApi.completeSnap(businessId, snap.snap_id);
      setAttention(remove);
      setRecommendations(remove);
      setPriority(remove);
    },
    [currentProfile?.id],
  );

  const markRecordRead = useCallback((messageId: string) => {
    if (!messageId.startsWith("record-")) return;
    const recordId = messageId.replace("record-", "");
    void recordsApi.markRecordRead(recordId).catch(() => {});
    setRecentRecords((prev) =>
      prev.map((item) =>
        item.id === messageId ? { ...item, read: true } : item,
      ),
    );
  }, []);

  const deleteRecord = useCallback(async (messageId: string) => {
    if (!messageId.startsWith("record-")) return;
    const recordId = messageId.replace("record-", "");
    await recordsApi.deleteRecord(recordId);
    setRecentRecords((prev) => prev.filter((item) => item.id !== messageId));
  }, []);

  return {
    currentProfile,
    recentRecords,
    insights,
    attention,
    recommendations,
    priority,
    loading,
    recordsTotal,
    recordsOffset,
    refresh,
    loadMoreRecords,
    actOnSnap,
    markRecordRead,
    deleteRecord,
  };
}

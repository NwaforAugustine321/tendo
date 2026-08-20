import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useEventReceiver } from "../../hooks/useEmitReceiver";

const DOCUMENT_PROCESSING_TOAST_ID = "document-processing";

export function showProcessingToast(message?: string) {
  toast.loading(message || "Processing document...", {
    id: DOCUMENT_PROCESSING_TOAST_ID,
  });
}

export function dismissProcessingToast(message?: string) {
  if (message) {
    toast.success(message, {
      id: DOCUMENT_PROCESSING_TOAST_ID,
      duration: 4000,
    });
  } else {
    toast.dismiss(DOCUMENT_PROCESSING_TOAST_ID);
  }
}

export function ProcessingNotification() {
  const { events, clear } = useEventReceiver(["document.progress"]);
  const lastProcessedRef = useRef(0);

  useEffect(() => {
    if (events.length <= lastProcessedRef.current) return;

    const newEvents = events.slice(lastProcessedRef.current);
    lastProcessedRef.current = events.length;

    for (const event of newEvents) {
      const data = event.data as any;
      const status = (data?.status || "").toLowerCase();
      const message = data?.message || "";

      if (status === "completed") {
        toast.success(message || "Document processing completed", {
          id: DOCUMENT_PROCESSING_TOAST_ID,
          duration: 4000,
        });
      } else if (status === "failed") {
        toast.error(message || "Document processing failed", {
          id: DOCUMENT_PROCESSING_TOAST_ID,
          duration: 4000,
        });
      } else if (status === "processing") {
        toast.loading(message || "Processing document...", {
          id: DOCUMENT_PROCESSING_TOAST_ID,
        });
      }
    }
  }, [events]);

  // Clear accumulated events periodically to avoid memory buildup
  useEffect(() => {
    if (events.length > 50) {
      lastProcessedRef.current = 0;
      clear();
    }
  }, [events.length, clear]);

  return null;
}

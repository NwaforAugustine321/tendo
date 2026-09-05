import { useEffect } from "react";

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

    return;
  }

  toast.dismiss(DOCUMENT_PROCESSING_TOAST_ID);
}

export function ProcessingNotification() {
  const { event, clearEvent } = useEventReceiver(["document.progress"]);

  useEffect(() => {
    if (!event) {
      return;
    }

    const data = event.data;

    const status =
      typeof data.status === "string" ? data.status.toLowerCase() : "";

    const message = typeof data.message === "string" ? data.message : "";

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

    clearEvent("document.progress");
  }, [event, clearEvent]);

  return null;
}

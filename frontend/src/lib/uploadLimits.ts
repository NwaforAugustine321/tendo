export type UploadKind = "image" | "audio" | "pdf" | "business";

const MB = 1024 * 1024;

function num(value: unknown, fallback: number): number {
  const parsed = Number(String(value ?? "").trim());
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const env = import.meta.env;

export const UPLOAD_LIMITS: Record<
  UploadKind,
  { label: string; maxBytes: number; maxSeconds?: number }
> = {
  image: {
    label: "Image",
    maxBytes: num(env.VITE_MAX_IMAGE_MB, 10) * MB,
  },
  audio: {
    label: "Audio",
    maxBytes: num(env.VITE_MAX_AUDIO_MB, 25) * MB,
    maxSeconds: num(env.VITE_MAX_AUDIO_MINUTES, 15) * 60,
  },
  pdf: {
    label: "PDF",
    maxBytes: num(env.VITE_MAX_PDF_MB, 20) * MB,
  },
  business: {
    label: "File",
    maxBytes: num(env.VITE_MAX_BUSINESS_FILE_MB, 10) * MB,
  },
};

function formatMb(bytes: number): string {
  return `${Math.round(bytes / MB)}MB`;
}

function formatMinutes(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}

function readAudioDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = document.createElement("audio");

    const finish = (duration: number | null) => {
      URL.revokeObjectURL(url);
      resolve(duration);
    };

    audio.preload = "metadata";
    audio.onloadedmetadata = () =>
      finish(Number.isFinite(audio.duration) ? audio.duration : null);
    audio.onerror = () => finish(null);
    audio.src = url;
  });
}

export function getUploadLimit(kind: string) {
  return UPLOAD_LIMITS[kind as UploadKind] ?? UPLOAD_LIMITS.business;
}

export async function checkUpload(
  kind: string,
  file: File,
): Promise<string | null> {
  const limit = getUploadLimit(kind);

  if (file.size > limit.maxBytes) {
    return `${limit.label} must be ${formatMb(limit.maxBytes)} or less. This file is ${formatMb(file.size)}.`;
  }

  if (limit.maxSeconds) {
    const duration = await readAudioDuration(file);

    if (duration !== null && duration > limit.maxSeconds) {
      return `${limit.label} must be ${formatMinutes(limit.maxSeconds)} or less. This file is ${formatMinutes(duration)}.`;
    }
  }

  return null;
}

import { ChevronLeft, MoreHorizontal } from "lucide-react";

import type { RecentActivityItem } from "./RecentActivity";

type ActivityDetailProps = {
  activity: RecentActivityItem;
  onBack: () => void;
};

function formatDate(date: string) {
  const timestamp = new Date(date).getTime();

  if (Number.isNaN(timestamp)) {
    return date;
  }

  return new Date(date).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatActivityType(title: string) {
  const value = title.toLowerCase();

  if (value.includes("learned")) {
    return "Learning";
  }

  if (value.includes("added")) {
    return "Business activity";
  }

  if (value.includes("updated")) {
    return "Update";
  }

  if (value.includes("found")) {
    return "Finding";
  }

  if (value.includes("reviewed")) {
    return "Review";
  }

  return "Business activity";
}

export default function ActivityDetail({
  activity,
  onBack,
}: ActivityDetailProps) {
  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="mx-auto w-full max-w-[900px] px-6 py-6 lg:px-8">
        {/* Back */}
        <button
          type="button"
          onClick={onBack}
          className="group mb-7 flex items-center gap-1.5 text-[11px] text-zinc-600 transition-colors hover:text-zinc-300"
        >
          <ChevronLeft
            size={14}
            className="transition-transform group-hover:-translate-x-0.5"
          />
          Recent Activity
        </button>

        {/* Header */}
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <h1 className="text-[20px] font-medium tracking-[-0.01em] text-zinc-100">
              {activity.title}
            </h1>

            <p className="mt-1.5 max-w-[650px] text-[12px] leading-5 text-zinc-500">
              {activity.message || "Tendo recorded this business activity."}
            </p>
          </div>

          <button
            type="button"
            aria-label="More options"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-zinc-800/70 bg-[#111111] text-zinc-600 transition-colors hover:border-zinc-700 hover:text-zinc-300"
          >
            <MoreHorizontal size={14} />
          </button>
        </div>

        {/* About */}
        <section className="mt-10">
          <SectionTitle>About</SectionTitle>

          <div className="mt-4 border-t border-zinc-800/60">
            <DetailRow
              label="Activity"
              value={formatActivityType(activity.title)}
            />

            <DetailRow label="When" value={formatDate(activity.date)} />

            <DetailRow
              label="Summary"
              value={
                activity.message ||
                "Tendo recorded this activity from your business activity."
              }
            />
          </div>
        </section>

        {/* What happened */}
        <section className="mt-10">
          <SectionTitle>What Happened</SectionTitle>

          <p className="mt-4 max-w-[700px] text-[13px] leading-6 text-zinc-400">
            {activity.message ||
              `${activity.title}. Tendo recorded this as part of your recent business activity.`}
          </p>
        </section>

        {/* What Tendo learned */}
        <section className="mt-10">
          <SectionTitle>What Tendo Learned</SectionTitle>

          <p className="mt-1.5 text-[11px] leading-5 text-zinc-600">
            This activity may contribute to what Tendo understands about your
            business.
          </p>

          <div className="mt-4 space-y-2">
            <div className="flex items-start gap-2.5 text-[12px] leading-5 text-zinc-400">
              <span className="mt-[8px] h-1 w-1 shrink-0 rounded-full bg-zinc-600" />

              <span>{activity.title}</span>
            </div>

            {activity.message && (
              <div className="flex items-start gap-2.5 text-[12px] leading-5 text-zinc-400">
                <span className="mt-[8px] h-1 w-1 shrink-0 rounded-full bg-zinc-600" />

                <span>{activity.message}</span>
              </div>
            )}
          </div>
        </section>

        {/* Activity */}
        <section className="mt-10 pb-10">
          <SectionTitle>Activity</SectionTitle>

          <div className="mt-4 border-t border-zinc-800/60">
            <div className="flex gap-5 border-b border-zinc-800/40 py-3.5">
              <span className="w-[90px] shrink-0 text-[10px] text-zinc-600">
                {new Date(activity.date).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })}
              </span>

              <div className="min-w-0">
                <p className="text-[12px] text-zinc-300">{activity.title}</p>

                {activity.message && (
                  <p className="mt-0.5 text-[11px] leading-5 text-zinc-600">
                    {activity.message}
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[180px_1fr] gap-6 border-b border-zinc-800/40 py-3.5">
      <span className="text-[11px] text-zinc-600">{label}</span>

      <span className="text-[12px] leading-5 text-zinc-300">{value}</span>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">
      {children}
    </h2>
  );
}

import {
  ArrowRight,
  ChevronLeft,
  MoreHorizontal,
  TriangleAlert,
} from "lucide-react";

export type AttentionDetailData = {
  id: string;
  title: string;
  action?: string;
  message?: string;
  detected?: string;
  area?: string;
  type?: string;
  whatHappened?: string;
  whyItNeedsAttention?: string;
  whatTendoKnows?: string[];
  whatYouCanDo?: string[];
  relatedActivity?: {
    id: string;
    title: string;
    date: string;
  }[];
};

type AttentionDetailProps = {
  attention: AttentionDetailData;
  onBack: () => void;
  onOpenActivity?: (id: string) => void;
};

function formatDate(date?: string) {
  if (!date) return "Recently";

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

export default function AttentionDetail({
  attention,
  onBack,
  onOpenActivity,
}: AttentionDetailProps) {
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
          What Needs Your Attention
        </button>

        {/* Header */}
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="mb-3 flex items-center gap-2">
              <TriangleAlert
                size={14}
                strokeWidth={1.8}
                className="shrink-0 text-amber-500/70"
              />

              <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-zinc-600">
                Needs attention
              </span>
            </div>

            <h1 className="text-[20px] font-medium tracking-[-0.02em] text-zinc-100">
              {attention.title}
            </h1>

            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-zinc-600">
              {attention.message ||
                "This may need your attention based on recent business activity."}
            </p>
          </div>

          <button
            type="button"
            className="mt-0.5 shrink-0 rounded-md p-1.5 text-zinc-600 transition-colors hover:bg-white/[0.04] hover:text-zinc-300"
            aria-label="More options"
          >
            <MoreHorizontal size={17} />
          </button>
        </div>

        {/* About */}
        <section className="mt-10">
          <SectionTitle>About</SectionTitle>

          <div className="mt-4 border-t border-zinc-800/60">
            <DetailRow
              label="Type"
              value={attention.type || "Business attention"}
            />

            <DetailRow
              label="Detected"
              value={formatDate(attention.detected)}
            />

            <DetailRow
              label="Area"
              value={attention.area || "Business activity"}
            />

            {attention.action && (
              <DetailRow label="Suggested action" value={attention.action} />
            )}
          </div>
        </section>

        {/* What Happened */}
        <section className="mt-10">
          <SectionTitle>What Happened</SectionTitle>

          <div className="mt-4">
            <p className="text-[13px] leading-7 text-zinc-400">
              {attention.whatHappened ||
                attention.message ||
                `${attention.title}. Tendo noticed this from recent business activity.`}
            </p>
          </div>
        </section>

        {/* Why It Needs Your Attention */}
        <section className="mt-10">
          <SectionTitle>Why It Needs Your Attention</SectionTitle>

          <div className="mt-4">
            <p className="text-[13px] leading-7 text-zinc-400">
              {attention.whyItNeedsAttention ||
                "This activity may require your attention because it differs from what Tendo normally sees or because it could affect your business."}
            </p>
          </div>
        </section>

        {/* What Tendo Knows */}
        <section className="mt-10">
          <SectionTitle>What Tendo Knows</SectionTitle>

          <div className="mt-4 space-y-4">
            {(attention.whatTendoKnows?.length
              ? attention.whatTendoKnows
              : [
                  "Tendo identified this from recent business activity.",
                  "Tendo is using related information to understand what may need your attention.",
                ]
            ).map((item, index) => (
              <div key={index} className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-700" />

                <p className="text-[13px] leading-6 text-zinc-400">{item}</p>
              </div>
            ))}
          </div>
        </section>

        {/* What You Can Do */}
        <section className="mt-10">
          <SectionTitle>What You Can Do</SectionTitle>

          <div className="mt-4 space-y-3">
            {(attention.whatYouCanDo?.length
              ? attention.whatYouCanDo
              : [
                  attention.action ||
                    "Review this activity and decide whether anything needs to be done.",
                ]
            ).map((item, index) => (
              <div
                key={index}
                className="flex items-start gap-3 border-b border-zinc-800/60 py-3.5"
              >
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500/60" />

                <p className="text-[13px] leading-6 text-zinc-400">{item}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Related Activity */}
        {attention.relatedActivity && attention.relatedActivity.length > 0 && (
          <section className="mt-10 pb-10">
            <SectionTitle>Related Activity</SectionTitle>

            <div className="mt-4 border-t border-zinc-800/60">
              {attention.relatedActivity.map((activity) => (
                <button
                  key={activity.id}
                  type="button"
                  onClick={() => onOpenActivity?.(activity.id)}
                  className="group flex w-full items-center gap-5 border-b border-zinc-800/60 py-4 text-left transition-colors hover:bg-white/[0.015]"
                >
                  <span className="shrink-0 text-[10px] text-zinc-700">
                    {formatDate(activity.date)}
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="block text-[12px] text-zinc-400 transition-colors group-hover:text-zinc-200">
                      {activity.title}
                    </span>
                  </span>

                  <ArrowRight
                    size={14}
                    className="shrink-0 text-zinc-800 transition-all group-hover:translate-x-0.5 group-hover:text-zinc-500"
                  />
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[180px_1fr] gap-6 border-b border-zinc-800/60 py-3.5">
      <span className="text-[11px] text-zinc-600">{label}</span>

      <span className="text-[12px] text-zinc-400">{value}</span>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[10px] font-medium uppercase tracking-[0.12em] text-zinc-600">
      {children}
    </h2>
  );
}

import {
  ArrowRight,
  ChevronLeft,
  MoreHorizontal,
  Sparkles,
} from "lucide-react";

export type InsightDetailData = {
  id: string;
  title: string;
  message?: string;
  detected?: string;
  area?: string;
  type?: string;
  whyItMatters?: string;
  whatTendoKnows?: string[];
  supportingInformation?: {
    label: string;
    value: string;
  }[];
  relatedActivity?: {
    id: string;
    title: string;
    date: string;
  }[];
};

type InsightDetailProps = {
  insight: InsightDetailData;
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

export default function InsightDetail({
  insight,
  onBack,
  onOpenActivity,
}: InsightDetailProps) {
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
          What Tendo Found
        </button>

        {/* Header */}
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles size={14} className="shrink-0 text-emerald-500/80" />

              <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-zinc-600">
                Insight
              </span>
            </div>

            <h1 className="text-[20px] font-medium tracking-[-0.02em] text-zinc-100">
              {insight.title}
            </h1>

            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-zinc-600">
              {insight.message ||
                "Tendo noticed a meaningful change in your business activity."}
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
              value={insight.type || "Business insight"}
            />

            <DetailRow label="Detected" value={formatDate(insight.detected)} />

            <DetailRow
              label="Area"
              value={insight.area || "Business activity"}
            />
          </div>
        </section>

        {/* What Tendo Found */}
        <section className="mt-10">
          <SectionTitle>What Tendo Found</SectionTitle>

          <div className="mt-4">
            <p className="text-[13px] leading-7 text-zinc-400">
              {insight.message ||
                `${insight.title}. Tendo identified this from recent business activity.`}
            </p>
          </div>
        </section>

        {/* Why It Matters */}
        <section className="mt-10">
          <SectionTitle>Why It Matters</SectionTitle>

          <div className="mt-4">
            <p className="text-[13px] leading-7 text-zinc-400">
              {insight.whyItMatters ||
                "This change may be useful when making decisions about your business. Tendo will continue watching related activity for meaningful changes."}
            </p>
          </div>
        </section>

        {/* What Tendo Knows */}
        <section className="mt-10">
          <SectionTitle>What Tendo Knows</SectionTitle>

          <div className="mt-4 space-y-4">
            {(insight.whatTendoKnows?.length
              ? insight.whatTendoKnows
              : [
                  "This insight was identified from recent business activity.",
                  "Tendo is using related activity to understand whether this is a meaningful change.",
                ]
            ).map((item, index) => (
              <div key={index} className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-700" />

                <p className="text-[13px] leading-6 text-zinc-400">{item}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Supporting Information */}
        {insight.supportingInformation &&
          insight.supportingInformation.length > 0 && (
            <section className="mt-10">
              <SectionTitle>Supporting Information</SectionTitle>

              <div className="mt-4 border-t border-zinc-800/60">
                {insight.supportingInformation.map((item) => (
                  <DetailRow
                    key={item.label}
                    label={item.label}
                    value={item.value}
                  />
                ))}
              </div>
            </section>
          )}

        {/* Related Activity */}
        {insight.relatedActivity && insight.relatedActivity.length > 0 && (
          <section className="mt-10 pb-10">
            <SectionTitle>Related Activity</SectionTitle>

            <div className="mt-4 border-t border-zinc-800/60">
              {insight.relatedActivity.map((activity) => (
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

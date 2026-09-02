import { ArrowRight, ChevronLeft, Clock3 } from "lucide-react";
import { useNavigate } from "react-router-dom";

export type RecentActivityItem = {
  id: string;
  title: string;
  date: string;
  message?: string;
};

type RecentActivityProps = {
  items?: RecentActivityItem[];
  onOpen?: (item: RecentActivityItem) => void;
};

const DUMMY_ACTIVITY: RecentActivityItem[] = [
  {
    id: "activity-1",
    title: "Tendo learned about Musa Ibrahim",
    date: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    message: "New customer information was added to what Tendo knows.",
  },
  {
    id: "activity-2",
    title: "You added Northern Foods",
    date: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    message: "Northern Foods was added to your business knowledge.",
  },
  {
    id: "activity-3",
    title: "Tendo updated order information",
    date: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    message: "Order information was updated from recent business activity.",
  },
  {
    id: "activity-4",
    title: "Tendo found a change in wholesale orders",
    date: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    message: "Wholesale orders have increased compared with recent activity.",
  },
  {
    id: "activity-5",
    title: "Customer information was updated",
    date: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    message: "Tendo noticed new information related to a customer.",
  },
  {
    id: "activity-6",
    title: "Tendo reviewed supplier activity",
    date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    message: "Recent supplier activity was reviewed.",
  },
];

function formatRelativeTime(date: string) {
  const timestamp = new Date(date).getTime();

  if (Number.isNaN(timestamp)) {
    return "";
  }

  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);

  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;

  const hours = Math.floor(minutes / 60);

  if (hours < 24) return `${hours}h`;

  const days = Math.floor(hours / 24);

  if (days < 7) return `${days}d`;

  return new Date(date).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });
}

export function RecentActivity({
  items = DUMMY_ACTIVITY,
  onOpen,
}: RecentActivityProps) {
  const navigate = useNavigate();

  return (
    <section className="w-full px-6 py-6 lg:px-10 lg:py-8">
      <div className="mx-auto w-full max-w-5xl">
        {/* Back */}
        <button
          type="button"
          onClick={() => navigate("/me")}
          className="group mb-7 flex items-center gap-1.5 text-[11px] text-zinc-600 transition-colors hover:text-zinc-300"
        >
          <ChevronLeft
            size={14}
            className="transition-transform group-hover:-translate-x-0.5"
          />
          Home
        </button>

        {/* Header */}
        <div className="mb-7">
          <div>
            <h2 className="text-[22px] font-medium tracking-[-0.02em] text-zinc-100">
              Recent Activity
            </h2>

            <p className="mt-1.5 text-[13px] text-zinc-600">
              A record of what happened in your business.
            </p>
          </div>
        </div>

        {/* Activity feed */}
        <div className="border-y border-zinc-800/60">
          {items.map((item, index) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onOpen?.(item)}
              className="group relative flex w-full items-start gap-5 px-2 py-5 text-left transition-colors hover:bg-white/[0.015]"
            >
              {/* Timeline */}
              <div className="relative flex w-5 shrink-0 justify-center">
                <span className="relative z-10 mt-1.5 h-2 w-2 shrink-0 rounded-full bg-zinc-700 transition-colors group-hover:bg-emerald-500/80" />

                {index < items.length - 1 && (
                  <span className="absolute left-1/2 top-4 h-[calc(100%+1px)] w-px -translate-x-1/2 bg-zinc-800/70" />
                )}
              </div>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <div className="flex items-start gap-4">
                  <p className="min-w-0 flex-1 text-[14px] font-medium text-zinc-300 transition-colors group-hover:text-zinc-100">
                    {item.title}
                  </p>

                  <span className="flex shrink-0 items-center gap-1.5 text-[10px] text-zinc-700">
                    <Clock3 size={11} />
                    {formatRelativeTime(item.date)}
                  </span>
                </div>

                {item.message && (
                  <p className="mt-1.5 max-w-3xl text-[12px] leading-relaxed text-zinc-600">
                    {item.message}
                  </p>
                )}
              </div>

              {/* Open indicator */}
              <ArrowRight
                size={15}
                className="mt-1 shrink-0 text-zinc-800 transition-all group-hover:translate-x-0.5 group-hover:text-zinc-500"
              />
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

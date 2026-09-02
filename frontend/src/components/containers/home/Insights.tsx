import { ArrowRight, ChevronLeft, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

export type Insight = {
  id: string;
  title: string;
  message?: string;
};

type InsightsProps = {
  items?: Insight[];
  onOpen?: (item: Insight) => void;
};

const DUMMY_INSIGHTS: Insight[] = [
  {
    id: "insight-1",
    title: "Wholesale orders increased 24%",
    message:
      "Tendo noticed a significant increase in wholesale orders compared with recent activity.",
  },
  {
    id: "insight-2",
    title: "Amina Stores is becoming a high-value customer",
    message:
      "Recent orders and purchase activity suggest that Amina Stores is becoming increasingly valuable.",
  },
  {
    id: "insight-3",
    title: "Customer activity is strongest on weekdays",
    message:
      "Most recent customer activity has been concentrated between Monday and Friday.",
  },
  {
    id: "insight-4",
    title: "Northern Foods has increased its order frequency",
    message:
      "Northern Foods has placed orders more frequently over the recent period.",
  },
  {
    id: "insight-5",
    title: "Several customers have not reordered recently",
    message:
      "Tendo noticed a group of customers whose recent activity has dropped compared with previous periods.",
  },
  {
    id: "insight-6",
    title: "Supplier activity has changed this month",
    message:
      "Recent supplier-related activity shows a noticeable change from the previous period.",
  },
];

export function Insights({ items = DUMMY_INSIGHTS, onOpen }: InsightsProps) {
  const navigate = useNavigate();

  const handleOpen = (item: Insight) => {
    if (onOpen) {
      onOpen(item);
      return;
    }

    navigate(`/me/insights/${item.id}`);
  };

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
        <div className="mb-6">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0">
              <h2 className="text-[22px] font-medium tracking-[-0.02em] text-zinc-100">
                What Tendo Found
              </h2>

              <p className="mt-1.5 text-[13px] text-zinc-600">
                Things Tendo has noticed from your business activity.
              </p>
            </div>

            {/* Attention link */}
            <button
              type="button"
              onClick={() => navigate("/me/attention")}
              className="group mt-1 flex shrink-0 items-center gap-1.5 text-[11px] font-medium text-red-400 transition-colors hover:text-red-300"
            >
              <span>What Needs Your Attention</span>

              <ArrowRight
                size={13}
                strokeWidth={1.8}
                className="transition-transform group-hover:translate-x-0.5"
              />
            </button>
          </div>
        </div>

        {/* Insights */}
        <div className="border-y border-zinc-800/50">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleOpen(item)}
              className="group flex w-full items-start gap-4 px-2 py-5 text-left transition-colors hover:bg-white/[0.015]"
            >
              {/* Insight icon */}
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
                <Sparkles
                  size={16}
                  strokeWidth={1.8}
                  className="text-zinc-600 transition-colors group-hover:text-emerald-400"
                />
              </span>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-medium text-zinc-300 transition-colors group-hover:text-zinc-100">
                  {item.title}
                </p>

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

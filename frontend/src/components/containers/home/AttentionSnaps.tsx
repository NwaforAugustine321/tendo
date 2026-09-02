import { ArrowRight, ChevronLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export type AttentionSnap = {
  id: string;
  title: string;
  action?: string;
  message?: string;
};

type AttentionSnapsProps = {
  items?: AttentionSnap[];
};

const DUMMY_ATTENTION: AttentionSnap[] = [
  {
    id: "attention-1",
    title: "Supplier payment is overdue",
    action: "Review",
    message: "A supplier payment appears to be past its expected payment date.",
  },
  {
    id: "attention-2",
    title: "Order #1042 may be delayed",
    action: "Review",
    message:
      "Recent activity suggests this order may not arrive within the expected timeframe.",
  },
  {
    id: "attention-3",
    title: "Cash flow changed this week",
    action: "View",
    message:
      "Tendo noticed a significant change in your recent cash flow activity.",
  },
  {
    id: "attention-4",
    title: "Northern Foods payment is approaching",
    action: "Review",
    message:
      "A payment associated with Northern Foods is approaching its expected date.",
  },
  {
    id: "attention-5",
    title: "Several customer orders need review",
    action: "Review",
    message:
      "Tendo found multiple orders with activity that may require your attention.",
  },
  {
    id: "attention-6",
    title: "Supplier activity has slowed",
    action: "View",
    message: "Recent supplier activity is lower than the previous period.",
  },
];

export function AttentionSnaps({
  items = DUMMY_ATTENTION,
}: AttentionSnapsProps) {
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
          <h2 className="text-[22px] font-medium tracking-[-0.02em] text-zinc-100">
            What Needs Your Attention
          </h2>

          <p className="mt-1.5 text-[13px] text-zinc-600">
            Things that may need you to take action.
          </p>
        </div>

        {/* Attention items */}
        <div className="border-y border-zinc-800/50">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => navigate(`/me/attention/${item.id}`)}
              className="group flex w-full items-start gap-4 px-2 py-5 text-left transition-colors hover:bg-white/[0.015]"
            >
              {/* Attention indicator */}
              <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-400/80 transition-colors group-hover:bg-amber-400" />

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

              {/* Action / Open indicator */}
              <div className="flex shrink-0 items-center gap-3">
                {item.action && (
                  <span className="text-[11px] text-zinc-600 transition-colors group-hover:text-zinc-400">
                    {item.action}
                  </span>
                )}

                <ArrowRight
                  size={15}
                  className="mt-0.5 text-zinc-800 transition-all group-hover:translate-x-0.5 group-hover:text-zinc-500"
                />
              </div>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

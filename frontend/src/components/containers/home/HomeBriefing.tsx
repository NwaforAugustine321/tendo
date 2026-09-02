import type { ReactNode } from "react";
import { ArrowRight, CheckCircle2, ChevronRight, Sparkles } from "lucide-react";
import { NavLink } from "react-router-dom";

import { HomeAskTendo } from "./HomeAskTendo";
import type { Snap } from "../../../lib/services/snaps";
import type { BusinessInsight } from "../../../lib/workspace/dashboard-types";
import type { InboxMessage } from "./types";

const ATTENTION_LIMIT = 3;
const FINDINGS_LIMIT = 3;
const ACTIVITY_LIMIT = 5;

function Section({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="mt-8">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-600">
          {title}
        </h2>

        {action}
      </div>

      <div className="divide-y divide-zinc-800/50">{children}</div>
    </section>
  );
}

function SectionLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <NavLink
      to={to}
      className="group flex items-center gap-1 text-[11px] text-zinc-600 transition-colors hover:text-zinc-300"
    >
      {children}

      <ArrowRight
        size={12}
        className="transition-transform group-hover:translate-x-0.5"
      />
    </NavLink>
  );
}

export function HomeBriefing({
  firstName,
  attention,
  insights,
  recentRecords,
  activityCount,
  onOpenRecord,
  onReview,
}: {
  firstName: string;
  attention: Snap[];
  insights: BusinessInsight[];
  recentRecords: InboxMessage[];
  activityCount: number;
  onAsk: (message: string) => void;
  onOpenRecord: (record: InboxMessage) => void;
  onReview: (snap: Snap) => void;
}) {
  const visibleAttention = attention.slice(0, ATTENTION_LIMIT);
  const visibleFindings = insights.slice(0, FINDINGS_LIMIT);
  const visibleActivity = recentRecords.slice(0, ACTIVITY_LIMIT);

  const hasMoreAttention = attention.length > ATTENTION_LIMIT;
  const hasMoreFindings = insights.length > FINDINGS_LIMIT;
  const hasMoreActivity = activityCount > ACTIVITY_LIMIT;

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10 lg:px-10 lg:py-12">
      {/* Greeting */}
      <div>
        <p className="text-[26px] font-medium tracking-[-0.025em] text-zinc-100">
          Good morning, {firstName}.
        </p>

        <p className="mt-1.5 text-[14px] text-zinc-500">
          A few things changed since you last checked in.
        </p>
      </div>

      {/* Ask Tendo */}
      <div className="mt-7">
        <HomeAskTendo />
      </div>

      {/* WHAT NEEDS YOUR ATTENTION */}
      <Section
        title="What needs your attention"
        action={
          attention.length > 0 ? (
            <SectionLink to="/me/attention">View all</SectionLink>
          ) : undefined
        }
      >
        {visibleAttention.length > 0 ? (
          visibleAttention.map((snap) => (
            <button
              key={snap.snap_id}
              type="button"
              onClick={() => onReview(snap)}
              className="group flex w-full items-center gap-3 py-3.5 text-left transition-colors hover:bg-white/[0.02]"
            >
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />

              <span className="min-w-0 flex-1 truncate text-[13px] text-zinc-300">
                {snap.title || snap.message}
              </span>

              <span className="shrink-0 text-[11px] text-zinc-600 transition-colors group-hover:text-zinc-400">
                Review
              </span>

              <ChevronRight
                size={14}
                className="shrink-0 text-zinc-700 group-hover:text-zinc-500"
              />
            </button>
          ))
        ) : (
          <div className="flex items-center gap-3 py-3.5 text-[13px] text-zinc-600">
            <CheckCircle2 size={15} className="text-emerald-500/70" />
            Nothing needs your attention right now.
          </div>
        )}
      </Section>

      {/* WHAT TENDO FOUND */}
      <Section
        title="What Tendo found"
        action={
          insights.length > 0 ? (
            <SectionLink to="/me/insights">See all</SectionLink>
          ) : undefined
        }
      >
        {visibleFindings.length > 0 ? (
          visibleFindings.map((insight, index) => (
            <NavLink
              key={insight.id || index}
              to={`/me/insights/${insight.id}`}
              className="group flex w-full items-center gap-3 py-3.5 text-left transition-colors hover:bg-white/[0.02]"
            >
              <Sparkles size={14} className="shrink-0 text-emerald-500/80" />

              <span className="min-w-0 flex-1 truncate text-[13px] text-zinc-300">
                {insight.insight}
              </span>

              <ArrowRight
                size={14}
                className="shrink-0 text-zinc-700 transition-colors group-hover:text-zinc-400"
              />
            </NavLink>
          ))
        ) : (
          <div className="py-3.5 text-[13px] text-zinc-600">
            Tendo is still learning from your business activity.
          </div>
        )}
      </Section>

      {/* WHILE YOU WERE AWAY */}
      <Section
        title="While you were away"
        action={
          activityCount > 0 ? (
            <SectionLink to="/me/activity">See what changed</SectionLink>
          ) : undefined
        }
      >
        <div className="flex items-center gap-3 py-3.5">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-800/70">
            <Sparkles size={13} className="text-zinc-500" />
          </span>

          <p className="text-[13px] leading-relaxed text-zinc-400">
            {activityCount > 0 ? (
              <>
                Tendo reviewed{" "}
                <span className="text-zinc-300">
                  {activityCount.toLocaleString()}
                </span>{" "}
                {activityCount === 1 ? "activity" : "activities"} while you were
                away.
              </>
            ) : (
              "Tendo hasn't seen any new business activity yet."
            )}
          </p>
        </div>
      </Section>

      {/* RECENT ACTIVITY */}
      <Section
        title="Recent activity"
        action={
          activityCount > 0 ? (
            <SectionLink to="/me/activity">View activity</SectionLink>
          ) : undefined
        }
      >
        {visibleActivity.length > 0 ? (
          visibleActivity.map((record) => (
            <button
              key={record.id}
              type="button"
              onClick={() => onOpenRecord(record)}
              className="group flex w-full items-center gap-3 py-3.5 text-left transition-colors hover:bg-white/[0.02]"
            >
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-700 transition-colors group-hover:bg-emerald-500/70" />

              <span className="min-w-0 flex-1 truncate text-[13px] text-zinc-400 group-hover:text-zinc-300">
                {record.sender || "Recent business activity"}
              </span>

              <span className="shrink-0 text-[11px] text-zinc-600">
                {record.date}
              </span>

              <ChevronRight
                size={14}
                className="shrink-0 text-zinc-700 group-hover:text-zinc-500"
              />
            </button>
          ))
        ) : (
          <div className="py-3.5 text-[13px] text-zinc-600">
            No recent activity yet.
          </div>
        )}
      </Section>
    </div>
  );
}

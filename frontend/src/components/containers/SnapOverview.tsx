import {
  Bar,
  BarChart,
  Cell,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, Bookmark, Layers, Target } from "lucide-react";
import clsx from "clsx";
import { GreetingHeader } from "./GreetingHeader";
import type { Snap } from "../../lib/services/snaps";
import type { SnapshotRecommendation } from "../../lib/services/snapshot";
import {
  buildSnapOverview,
  toPercent,
} from "../../lib/workspace/snap-analytics";

type Props = {
  active: Snap[];
  saved: Snap[];
  businessName?: string;
  loading?: boolean;
};

/** Shared row shape for every chart, so one tooltip serves all of them. */
type ChartRow = {
  name: string;
  count: number;
  percent: number;
  confidence?: number;
  urgent?: number;
  steady?: number;
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#f87171",
  high: "#f87171",
  medium: "#fbbf24",
  low: "#71717a",
};

const TYPE_COLORS: Record<string, string> = {
  warning: "#f87171",
  attention: "#fb923c",
  opportunity: "#c084fc",
  recommendation: "#fbbf24",
};

const URGENT_COLOR = "#f87171";
const STEADY_COLOR = "#3ecf8e";

const AXIS_TICK = { fontSize: 9, fill: "#71717a" };
const CURSOR = { fill: "rgba(255,255,255,0.04)" };

/** Chart bodies are capped so cards stay compact instead of stretching. */
const CHART_HEIGHT = "h-[136px]";

/** GreetingHeader derives business health from high/medium counts. */
function toGreetingInput(snaps: Snap[]): SnapshotRecommendation[] {
  return snaps.map((snap) => ({
    action: snap.title,
    reason: snap.why_it_matters,
    priority: snap.priority === "critical" ? "high" : snap.priority,
  }));
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: ChartRow }[];
}) {
  if (!active || !payload?.length) return null;

  const row = payload[0].payload;

  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-[11px] shadow-lg">
      <p className="font-medium capitalize text-zinc-100">{row.name}</p>
      <p className="mt-1 text-zinc-400">
        {row.count} signals · {row.percent}%
      </p>
      {row.confidence !== undefined && (
        <p className="text-zinc-400">{row.confidence}% avg confidence</p>
      )}
      {!!row.urgent && <p className="text-red-400">{row.urgent} urgent</p>}
    </div>
  );
}

function Panel({
  title,
  children,
  legend,
}: {
  title: string;
  children: React.ReactNode;
  legend?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-zinc-800/40 bg-[#0f0f0f] p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-[9px] font-medium uppercase tracking-wider text-zinc-500">
          {title}
        </h2>
        {legend}
      </div>
      {children}
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1 text-[9px] text-zinc-500">
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}

function Indicator({
  icon: Icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: typeof Target;
  label: string;
  value: string;
  hint?: string;
  tone?: string;
}) {
  return (
    <div className="rounded-lg border border-zinc-800/40 bg-[#0f0f0f] p-3">
      <div className="flex items-center gap-1.5 text-zinc-500">
        <Icon size={12} className={tone} />
        <span className="text-[9px] font-medium uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p
        className={clsx(
          "mt-1.5 text-[17px] font-medium leading-none",
          tone || "text-zinc-200",
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-[10px] text-zinc-500">{hint}</p>}
    </div>
  );
}

/** Radial gauge for a single 0..100 percentage. */
function Gauge({
  percent,
  color,
  caption,
}: {
  percent: number;
  color: string;
  caption: string;
}) {
  return (
    <div className={clsx("relative", CHART_HEIGHT)}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          data={[{ value: percent }]}
          innerRadius="74%"
          outerRadius="98%"
          startAngle={210}
          endAngle={-30}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            dataKey="value"
            angleAxisId={0}
            cornerRadius={6}
            fill={color}
            background={{ fill: "#27272a" }}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[17px] font-medium text-zinc-200">
          {percent}%
        </span>
        <span className="text-[9px] text-zinc-500">{caption}</span>
      </div>
    </div>
  );
}

export function SnapOverview({ active, saved, businessName, loading }: Props) {
  const overview = buildSnapOverview(active, saved);

  const greeting = (
    <GreetingHeader
      name={businessName || "there"}
      recommendations={toGreetingInput([...active, ...saved])}
    />
  );

  if (loading) {
    return (
      <div className="flex flex-col">
        {greeting}
        <div className="grid grid-cols-1 gap-4 px-6 pb-6 sm:grid-cols-2 xl:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="h-[104px] animate-pulse rounded-lg border border-zinc-800/40 bg-[#0f0f0f]"
            />
          ))}
        </div>
      </div>
    );
  }

  if (overview.total === 0) {
    return (
      <div className="flex flex-col">
        {greeting}
        <div className="flex items-center justify-center py-16">
          <div className="px-6 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800/60">
              <Layers size={22} className="text-zinc-500" />
            </div>
            <p className="text-[14px] font-medium text-zinc-300">
              No signals to summarise
            </p>
            <p className="mt-1 text-[12px] text-zinc-500">
              Once Tendo surfaces Snaps, this overview breaks them down by
              priority, category, and domain.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const confidencePercent = toPercent(overview.avgConfidence);
  const urgentPercent = toPercent(overview.urgentShare);

  const priorityData: ChartRow[] = overview.priorities.map((slice) => ({
    name: slice.key,
    count: slice.count,
    percent: toPercent(slice.share),
  }));

  const typeData: ChartRow[] = overview.types.map((slice) => ({
    name: slice.key,
    count: slice.count,
    percent: toPercent(slice.share),
  }));

  const domainData: ChartRow[] = overview.domains.map((slice) => ({
    name: slice.key,
    count: slice.count,
    percent: toPercent(slice.share),
    confidence: toPercent(slice.avgConfidence),
    urgent: slice.urgentCount,
    steady: slice.count - slice.urgentCount,
  }));

  return (
    <div className="flex flex-col">
      {greeting}

      <div className="flex flex-col gap-4 px-6 pb-6">
        {/* KPI strip */}
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <Indicator
            icon={Layers}
            label="Total signals"
            value={String(overview.total)}
            hint={`${overview.activeCount} live · ${overview.savedCount} saved`}
          />
          <Indicator
            icon={AlertTriangle}
            label="Needs urgency"
            value={`${urgentPercent}%`}
            hint={`${overview.urgentCount} high or critical`}
            tone={urgentPercent >= 50 ? "text-red-400" : undefined}
          />
          <Indicator
            icon={Target}
            label="Avg confidence"
            value={`${confidencePercent}%`}
            hint="Across all signals"
          />
          <Indicator
            icon={Bookmark}
            label="Domains affected"
            value={String(overview.domains.length)}
            hint={
              overview.domains[0]
                ? `Top: ${overview.domains[0].key}`
                : undefined
            }
          />
        </div>

        {/* Gauges beside priority distribution */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Panel title="Confidence">
            <Gauge
              percent={confidencePercent}
              color={STEADY_COLOR}
              caption="average certainty"
            />
          </Panel>

          <Panel title="Urgency load">
            <Gauge
              percent={urgentPercent}
              color={urgentPercent >= 50 ? URGENT_COLOR : "#fbbf24"}
              caption="high or critical"
            />
          </Panel>

          <Panel title="Priority mix">
            <div className={CHART_HEIGHT}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={priorityData} barSize={18}>
                  <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={AXIS_TICK}
                  />
                  <YAxis hide />
                  <Tooltip cursor={CURSOR} content={<ChartTooltip />} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {priorityData.map((row) => (
                      <Cell key={row.name} fill={PRIORITY_COLORS[row.name]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>

        {/* Category beside domain urgency breakdown */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Panel title="Category">
            <div className={CHART_HEIGHT}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={typeData} layout="vertical" barSize={12}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={88}
                    axisLine={false}
                    tickLine={false}
                    tick={AXIS_TICK}
                  />
                  <Tooltip cursor={CURSOR} content={<ChartTooltip />} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {typeData.map((row) => (
                      <Cell key={row.name} fill={TYPE_COLORS[row.name]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel
            title="Domain analysis"
            legend={
              <div className="flex items-center gap-3">
                <LegendDot color={URGENT_COLOR} label="urgent" />
                <LegendDot color={STEADY_COLOR} label="steady" />
              </div>
            }
          >
            <div className={CHART_HEIGHT}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={domainData} layout="vertical" barSize={12}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={88}
                    axisLine={false}
                    tickLine={false}
                    tick={AXIS_TICK}
                  />
                  <Tooltip cursor={CURSOR} content={<ChartTooltip />} />
                  <Bar dataKey="urgent" stackId="domain" fill={URGENT_COLOR} />
                  <Bar
                    dataKey="steady"
                    stackId="domain"
                    fill={STEADY_COLOR}
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

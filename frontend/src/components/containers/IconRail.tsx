import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
  Lightbulb,
  History,
  BarChart3,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAuth } from "../../context/auth";
import type { PrimarySection } from "../../lib/navigation";

type Props = {
  orientation?: "vertical" | "horizontal";
  onNavigate?: () => void;
  activePrimary: PrimarySection;
  onPrimaryClick?: () => void;
  onToggleSecondary?: () => void;
  secondaryVisible?: boolean;
};

function railItemClass(
  active: boolean,
  orientation: "vertical" | "horizontal",
) {
  const edge = orientation === "vertical" ? "border-l-2" : "border-b-2";
  if (orientation === "vertical") {
    return [
      "relative z-0 flex h-11 w-full items-center justify-center gap-0 overflow-hidden rounded-r-md",
      "transition-[background-color,color,box-shadow,gap,padding] duration-200 ease-out",
      "group-hover/rail:justify-start group-hover/rail:gap-2 group-hover/rail:bg-[#141414] group-hover/rail:px-2.5 group-hover/rail:shadow-lg",
      edge,
      active
        ? "border-[#3ecf8e] bg-white/[0.06] text-white"
        : "border-transparent text-zinc-400 hover:text-zinc-300",
    ].join(" ");
  }
  return [
    "relative z-0 flex h-10 w-11 shrink-0 items-center justify-center gap-0 overflow-hidden rounded-md",
    "transition-[min-width,background-color,color,box-shadow,gap,padding] duration-200 ease-out",
    "group-hover/rail:min-w-[8.25rem] group-hover/rail:justify-start group-hover/rail:bg-[#141414] group-hover/rail:px-2 group-hover/rail:shadow-md",
    edge,
    active
      ? "border-[#3ecf8e] bg-white/[0.06] text-white"
      : "border-transparent text-zinc-400 hover:text-zinc-300",
  ].join(" ");
}

const railItemLabelClass =
  "pointer-events-none max-w-0 truncate whitespace-nowrap text-left text-xs font-medium text-zinc-400 opacity-0 transition-[max-width,opacity] duration-200 ease-out group-hover/rail:max-w-[7.5rem] group-hover/rail:opacity-100";

const NAV_ITEMS: {
  id: PrimarySection;
  to: string;
  label: string;
  icon: ReactNode;
}[] = [
  {
    id: "insights",
    to: "/me/insights",
    label: "Insights",
    icon: <Lightbulb size={20} />,
  },
  {
    id: "recent",
    to: "/me/recent",
    label: "Recent",
    icon: <History size={20} />,
  },
  {
    id: "analytics",
    to: "/me/analytics",
    label: "Analytics",
    icon: <BarChart3 size={20} />,
  },
];

export function IconRail({
  orientation = "vertical",
  onNavigate,
  activePrimary,
  onPrimaryClick,
  onToggleSecondary,
  secondaryVisible,
}: Props) {
  const { user } = useAuth();
  const fireClick = () => {
    onPrimaryClick?.();
    onNavigate?.();
  };

  const core = (
    <>
      {NAV_ITEMS.map((item) => (
        <div
          key={item.id}
          className={
            orientation === "vertical"
              ? "h-11 w-full shrink-0"
              : "h-10 shrink-0"
          }
        >
          <NavLink
            to={item.to}
            end={item.to === "/me"}
            className={() =>
              railItemClass(activePrimary === item.id, orientation)
            }
            aria-label={item.label}
            onClick={fireClick}
          >
            <span className="flex shrink-0 items-center justify-center">
              {item.icon}
            </span>
            <span className={railItemLabelClass}>{item.label}</span>
          </NavLink>
        </div>
      ))}
    </>
  );

  if (orientation === "horizontal") {
    return (
      <div
        className="group/rail flex w-full flex-row items-center gap-1 overflow-x-auto overflow-y-visible border-b border-zinc-800/90 bg-[#0f0f0f] px-2 py-1"
        onClick={onNavigate}
      >
        {core}
      </div>
    );
  }

  return (
    <aside
      className="group/rail pointer-events-auto absolute inset-y-0 left-0 z-30 flex w-[52px] flex-col overflow-visible border-r border-zinc-800/90 bg-[#0f0f0f] shadow-none transition-[width,box-shadow] duration-200 ease-out hover:w-44 hover:shadow-2xl"
      aria-label="Primary navigation"
      onMouseEnter={() => window.dispatchEvent(new Event("tendo:rail-enter"))}
      onMouseLeave={() => window.dispatchEvent(new Event("tendo:rail-leave"))}
    >
      <div className="flex w-full flex-col overflow-visible py-2">{core}</div>
      <div className="min-h-0 flex-1" aria-hidden="true" />
      <div className="mt-auto flex w-full flex-col overflow-visible border-t border-zinc-800/90 py-2">
        <div className="flex h-11 w-full shrink-0 items-center justify-center gap-2 group-hover/rail:justify-start group-hover/rail:px-2.5">
          <div className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 transition-colors hover:border-zinc-600 hover:bg-zinc-700">
            <span className="text-[11px] font-bold text-zinc-400">
              {(user?.name || "U")[0].toUpperCase()}
            </span>
          </div>
          <span className="pointer-events-none max-w-0 truncate whitespace-nowrap text-xs font-medium text-zinc-400 opacity-0 transition-[max-width,opacity] duration-200 ease-out group-hover/rail:max-w-[7.5rem] group-hover/rail:opacity-100">
            {user?.name || "User"}
          </span>
        </div>
        {onToggleSecondary && (
          <div className="h-11 w-full shrink-0">
            <button
              type="button"
              onClick={onToggleSecondary}
              className={railItemClass(false, orientation)}
              aria-label="Toggle sidebar"
              title={secondaryVisible ? "Collapse sidebar" : "Expand sidebar"}
            >
              <span className="flex shrink-0 items-center justify-center">
                {secondaryVisible ? (
                  <PanelLeftClose size={20} />
                ) : (
                  <PanelLeftOpen size={20} />
                )}
              </span>
              <span className={railItemLabelClass}>
                {secondaryVisible ? "Collapse" : "Expand"}
              </span>
            </button>
          </div>
        )}
        <div className="h-11 w-full shrink-0">
          <NavLink
            to="/me/settings"
            className={() => railItemClass(false, orientation)}
            aria-label="Settings"
            onClick={fireClick}
          >
            <span className="flex shrink-0 items-center justify-center">
              <Settings size={20} />
            </span>
            <span className={railItemLabelClass}>Settings</span>
          </NavLink>
        </div>
      </div>
    </aside>
  );
}

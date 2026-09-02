import { useState, useEffect } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import {
  Home,
  Sparkles,
  FileText,
  Lightbulb,
  History,
  Settings,
  Plus,
  Menu,
} from "lucide-react";
import clsx from "clsx";

import { useAuth } from "../../context/auth";

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
  end?: boolean;
};

const PRIMARY_NAV: NavItem[] = [
  {
    to: "/me",
    label: "Home",
    icon: <Home size={18} />,
    end: true,
  },
  {
    to: "/me/knowledge",
    label: "What I Know",
    icon: <Sparkles size={18} />,
  },
  {
    to: "/me/mems",
    label: "Memory",
    icon: <FileText size={18} />,
  },
  {
    to: "/me/insights",
    label: "What I Found",
    icon: <Lightbulb size={18} />,
  },
  {
    to: "/me/activity",
    label: "Activity",
    icon: <History size={18} />,
  },
];

type SidebarProps = {
  className?: string;
  collapsed: boolean;
  onToggle: () => void;
};

function NavigationItem({
  item,
  collapsed,
}: {
  item: NavItem;
  collapsed: boolean;
}) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        clsx(
          "group flex items-center transition-colors",
          collapsed
            ? "mx-auto h-9 w-9 justify-center rounded-lg"
            : "gap-3 py-1.5 pl-4 pr-3 text-[12px] font-medium",
          isActive
            ? "bg-emerald-500/15 text-emerald-400"
            : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200",
        )
      }
    >
      <span className="shrink-0">{item.icon}</span>

      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );
}

export function Sidebar({ className, collapsed, onToggle }: SidebarProps) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [documentsOpen, setDocumentsOpen] = useState(
    location.pathname.startsWith("/me/files"),
  );

  useEffect(() => {
    if (location.pathname.startsWith("/me/files")) {
      setDocumentsOpen(true);
    }
  }, [location.pathname]);

  const handleAdd = () => {
    navigate("/me/knowledge");
  };

  const settingsActive =
    location.pathname === "/me/settings" || location.pathname === "/me/profile";

  return (
    <aside
      className={clsx(
        "flex h-full flex-col",
        "border-r border-zinc-800/60",
        "bg-[#0f0f0f]",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-[68px]" : "w-[220px]",
        className,
      )}
      aria-label="Main navigation"
    >
      {/* HEADER */}
      <div
        className={clsx(
          "flex items-center gap-2 px-3 py-3",
          collapsed && "flex-col gap-3",
        )}
      >
        <button
          type="button"
          onClick={onToggle}
          className={clsx(
            "flex h-9 w-9 shrink-0",
            "items-center justify-center",
            "rounded-full",
            "text-zinc-400",
            "transition-colors",
            "hover:bg-white/5",
            "hover:text-zinc-200",
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Menu size={20} />
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={handleAdd}
          className={clsx(
            "flex h-8 w-8",
            "items-center justify-center",
            "rounded-lg",
            "border border-zinc-700/80",
            "bg-zinc-800",
            "text-zinc-200",
            "shadow-sm",
            "transition-all",
            "hover:border-zinc-600",
            "hover:bg-zinc-750",
            "hover:shadow-md",
            "active:scale-[0.97]",
          )}
          title="Go to What I Know"
          aria-label="Go to What I Know"
        >
          <Plus size={15} />
        </button>
      </div>

      {/* PRIMARY NAVIGATION */}
      <nav
        className={clsx(
          "flex flex-col gap-0.5 py-1",
          collapsed ? "px-1.5" : "px-0",
        )}
      >
        <NavigationItem item={PRIMARY_NAV[0]} collapsed={collapsed} />

        <NavigationItem item={PRIMARY_NAV[1]} collapsed={collapsed} />

        {/* DOCUMENTS */}
        <NavigationItem item={PRIMARY_NAV[2]} collapsed={collapsed} />

        <NavigationItem item={PRIMARY_NAV[3]} collapsed={collapsed} />

        <NavigationItem item={PRIMARY_NAV[4]} collapsed={collapsed} />
      </nav>

      {/* SPACER */}
      <div className="flex-1" />

      {/* SETTINGS */}
      <div
        className={clsx(
          "border-t border-zinc-800/60",
          collapsed ? "px-1.5 py-2" : "px-0",
        )}
      >
        <NavLink
          to="/me/profile"
          title={collapsed ? "Settings" : undefined}
          className={clsx(
            "flex items-center",
            "transition-colors",
            collapsed
              ? "mx-auto h-9 w-9 justify-center rounded-lg"
              : "gap-3 py-[0.8rem] pl-4 pr-3 text-[12px] font-medium",
            settingsActive
              ? "bg-emerald-500/15 text-emerald-400"
              : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200",
          )}
        >
          <Settings size={18} className="shrink-0" />

          {!collapsed && <span className="truncate">Settings</span>}
        </NavLink>
      </div>

      {/* USER */}
      <div className="border-t border-zinc-800/60 px-3 py-3">
        <button
          type="button"
          onClick={() => navigate("/me/profile")}
          title="View profile"
          className={clsx(
            "flex w-full items-center",
            "rounded-lg",
            "transition-colors",
            "hover:bg-white/5",
            collapsed ? "justify-center p-1" : "gap-2.5 px-1 py-1",
          )}
        >
          <div
            className={clsx(
              "flex h-8 w-8 shrink-0",
              "items-center justify-center",
              "rounded-full",
              "border",
              "border-zinc-700 bg-zinc-800",
            )}
          >
            <span className="text-[11px] font-bold text-zinc-400">
              {(user?.name || "U").charAt(0).toUpperCase()}
            </span>
          </div>

          {!collapsed && (
            <div className="min-w-0 flex-1 text-left">
              <p className="truncate text-[12px] font-medium text-zinc-300">
                {user?.name || "User"}
              </p>

              <p className="truncate text-[10px] text-zinc-500">
                {user?.email || ""}
              </p>
            </div>
          )}
        </button>
      </div>
    </aside>
  );
}

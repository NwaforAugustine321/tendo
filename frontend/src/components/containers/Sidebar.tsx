import { useState, useEffect, useCallback } from "react";
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
  MessageCircle,
  ChevronDown,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

import { useAuth } from "../../context/auth";
import { useBusinessStore } from "../../store/business";
import {
  listDataSources,
  disconnectDataSource,
  onboardWhatsApp,
} from "../../lib/services/integrations";

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
    to: "/me/files",
    label: "Documents",
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

const CODE =
  "AQIZMgohzOX1Fg8BH7E26-3iuwLKboSSEpaR6vUoIIZXpL60lsyoLFE4yVXB5mlbHO6QbtTA445X5C3U0pTScMYEBikNeugXjSdT8JiqAJxkt6JqETYfssDVGyxiBZWZ3CMhixaNwNSRQ7afdL98eSGuTAg-8G50mD7IP_WdUEUENCjkeb_DRC3ti32hAWXNnS8cK0QT1lMk1J2WbiBCaBBfXHirG3-cWfeNTOQzvX3G5La1NG3ODwpKcmp95LsV99cJalQZnKOYAI65NkiwjNLRmPCnXHGRO_rFJl6NGaeWit_NqNrY1Lwus-t_BKhQKbdCXAhMaAsWb7LftkxZq8mvymeb9rNbo3tJ4HXcazO4tsHkMObO_DC2JWIWWlfis45SOtV8FHqkbivxeyzfGOpHCJ7AGJEzWr00JD0gBS2iNQ";

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

  const { currentProfile } = useBusinessStore();

  const [whatsappConnected, setWhatsappConnected] = useState(false);

  const [documentsOpen, setDocumentsOpen] = useState(
    location.pathname.startsWith("/me/files"),
  );

  useEffect(() => {
    if (location.pathname.startsWith("/me/files")) {
      setDocumentsOpen(true);
    }
  }, [location.pathname]);

  const fetchWhatsAppStatus = useCallback(async () => {
    if (!currentProfile?.id) return;

    try {
      const sources = await listDataSources(currentProfile.id);

      const wa = sources.find(
        (source) =>
          source.source_type === "whatsapp" && source.status === "active",
      );

      setWhatsappConnected(!!wa);
    } catch {
      setWhatsappConnected(false);
    }
  }, [currentProfile?.id]);

  useEffect(() => {
    fetchWhatsAppStatus();
  }, [fetchWhatsAppStatus]);

  const handleConnectWhatsApp = async () => {
    if (!currentProfile?.id) return;

    if (whatsappConnected) {
      try {
        await disconnectDataSource(currentProfile.id, "whatsapp");

        setWhatsappConnected(false);
      } catch {
        toast.error("Couldn't disconnect WhatsApp. Please try again.");
      }

      return;
    }

    try {
      const WHATSAPP_CONFIG_ID = import.meta.env.VITE_WHATSAPP_CONFIG_ID;

      if (!WHATSAPP_CONFIG_ID) {
        toast.error("WhatsApp connection is not configured.");
        return;
      }

      const FB = (window as any).FB;

      if (!FB) {
        toast.error("WhatsApp connection is unavailable right now.");
        return;
      }

      onboardWhatsApp(currentProfile.id, CODE).then(() => {
        setWhatsappConnected(true);
      });
    } catch {
      toast.error("Couldn't connect WhatsApp. Please try again.");
    }
  };

  const handleAdd = () => {
    navigate("/me/knowledge");
  };

  const settingsActive =
    location.pathname === "/me/settings" || location.pathname === "/me/profile";

  const documentsActive = location.pathname.startsWith("/me/files");

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

        {/* Documents + WhatsApp */}
        <div>
          <NavLink
            to="/me/files"
            end
            title={collapsed ? "Documents" : undefined}
            onClick={() => {
              setDocumentsOpen(true);
            }}
            className={clsx(
              "group flex items-center transition-colors",
              collapsed
                ? "mx-auto h-9 w-9 justify-center rounded-lg"
                : "gap-3 py-1.5 pl-4 pr-3 text-[12px] font-medium",
              documentsActive
                ? "bg-emerald-500/15 text-emerald-400"
                : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200",
            )}
          >
            <FileText size={18} className="shrink-0" />

            {!collapsed && (
              <>
                <span className="min-w-0 flex-1 truncate text-left">
                  Documents
                </span>

                <button
                  type="button"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();

                    setDocumentsOpen((open) => !open);
                  }}
                  className={clsx(
                    "flex h-5 w-5",
                    "items-center justify-center",
                    "rounded",
                    "transition-colors",
                    "hover:bg-white/5",
                  )}
                  aria-label={
                    documentsOpen ? "Collapse Documents" : "Expand Documents"
                  }
                >
                  <ChevronDown
                    size={13}
                    className={clsx(
                      "transition-transform",
                      !documentsOpen && "-rotate-90",
                    )}
                  />
                </button>
              </>
            )}
          </NavLink>

          {!collapsed && documentsOpen && (
            <div className="ml-[27px] mt-[0.4rem] border-l border-zinc-800/80 pl-3">
              <button
                type="button"
                onClick={handleConnectWhatsApp}
                className={clsx(
                  "flex w-full items-center gap-2",
                  "rounded-md",
                  "px-2 py-1.5",
                  "text-[11px]",
                  "transition-colors",
                  whatsappConnected
                    ? "text-emerald-400 hover:bg-emerald-500/5"
                    : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300",
                )}
              >
                <MessageCircle size={14} className="shrink-0" />

                <span className="min-w-0 flex-1 truncate text-left">
                  WhatsApp
                </span>

                {whatsappConnected && (
                  <span className="shrink-0 text-[9px] font-medium text-emerald-500/80">
                    Connected
                  </span>
                )}
              </button>
            </div>
          )}

          {collapsed && (
            <button
              type="button"
              onClick={handleConnectWhatsApp}
              title={
                whatsappConnected ? "WhatsApp connected" : "Connect WhatsApp"
              }
              aria-label={
                whatsappConnected ? "WhatsApp connected" : "Connect WhatsApp"
              }
              className={clsx(
                "mx-auto mt-0.5 flex h-7 w-7",
                "items-center justify-center",
                "rounded-md",
                "text-zinc-500",
                "transition-colors",
                "hover:bg-white/5",
                "hover:text-zinc-300",
              )}
            >
              <MessageCircle size={15} />
            </button>
          )}
        </div>

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

import { useMemo, useState } from "react";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronRight as ChevronRightIcon,
  Folder,
  HardDrive,
  Mail,
  MessageCircle,
  Plus,
  RefreshCw,
  Trash2,
  Video,
  X,
} from "lucide-react";

import type { DocumentSource } from "../documents.types";

type Props = {
  sources: DocumentSource[];
  onSourcesChange?: (sources: DocumentSource[]) => void;
};

type ConnectOption = "folder" | "whatsapp" | "email" | "google-meet";

const SOURCES_PER_PAGE = 10;

export default function DocumentsSources({ sources, onSourcesChange }: Props) {
  const [showConnect, setShowConnect] = useState(false);

  const [isConnecting, setIsConnecting] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);

  const connectedSources = useMemo(
    () => sources.filter((source) => source.connected),
    [sources],
  );

  const totalPages = Math.max(
    1,
    Math.ceil(connectedSources.length / SOURCES_PER_PAGE),
  );

  const paginatedSources = useMemo(() => {
    const start = (currentPage - 1) * SOURCES_PER_PAGE;

    const end = start + SOURCES_PER_PAGE;

    return connectedSources.slice(start, end);
  }, [connectedSources, currentPage]);

  const handleConnectFolder = async () => {
    setIsConnecting(true);

    try {
      /*
       * Use the browser File System Access API
       * when it is available.
       */
      if ("showDirectoryPicker" in window) {
        const picker = (
          window as typeof window & {
            showDirectoryPicker?: () => Promise<{
              name: string;
            }>;
          }
        ).showDirectoryPicker;

        if (!picker) {
          return;
        }

        const directory = await picker();

        const newSource: DocumentSource = {
          id: `source-${Date.now()}`,
          name: directory.name,
          type: "folder",
          connected: true,
          createdAt: "Just now",
          updatedAt: "Just now",
        };

        onSourcesChange?.([...sources, newSource]);

        setCurrentPage(
          Math.max(
            1,
            Math.ceil((connectedSources.length + 1) / SOURCES_PER_PAGE),
          ),
        );

        setShowConnect(false);

        return;
      }

      console.warn("Folder selection is not supported by this browser.");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      console.error("Failed to connect folder:", error);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleConnectService = (option: ConnectOption) => {
    if (option === "folder") {
      void handleConnectFolder();
      return;
    }

    /*
     * OAuth / integration flows for these services
     * will be connected here later.
     */
    console.info(`Connect ${getConnectOptionLabel(option)} integration`);

    setShowConnect(false);
  };

  const handleDisconnect = (sourceId: string) => {
    const source = sources.find((item) => item.id === sourceId);

    if (!source) {
      return;
    }

    const confirmed = window.confirm(
      `Disconnect "${source.name}"? Documents already imported from this source will remain.`,
    );

    if (!confirmed) {
      return;
    }

    const nextSources = sources.map((item) =>
      item.id === sourceId
        ? {
            ...item,
            connected: false,
          }
        : item,
    );

    onSourcesChange?.(nextSources);

    const nextConnectedCount = connectedSources.length - 1;

    const nextTotalPages = Math.max(
      1,
      Math.ceil(nextConnectedCount / SOURCES_PER_PAGE),
    );

    setCurrentPage((page) => Math.min(page, nextTotalPages));
  };

  const handleReconnect = (sourceId: string) => {
    onSourcesChange?.(
      sources.map((item) =>
        item.id === sourceId
          ? {
              ...item,
              connected: true,
              updatedAt: "Just now",
            }
          : item,
      ),
    );
  };

  const goToPreviousPage = () => {
    setCurrentPage((page) => Math.max(1, page - 1));
  };

  const goToNextPage = () => {
    setCurrentPage((page) => Math.min(totalPages, page + 1));
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* HEADER */}
      <div className="shrink-0 border-b border-zinc-800/70">
        <div className="flex items-center justify-between gap-4 px-6 py-2">
          <div>
            <p className="mt-1 text-[11px] text-zinc-500">
              Connect places where Tendo can find your documents and
              information.
            </p>
          </div>

          {/* CONNECT SOURCE */}
          <button
            type="button"
            onClick={() => setShowConnect(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-zinc-800 bg-[#151515] px-3 text-[10px] font-medium text-zinc-400 transition-colors hover:border-zinc-700 hover:bg-[#191919] hover:text-zinc-200"
          >
            <Plus size={13} />
            Connect source
          </button>
        </div>
      </div>

      {/* CONTENT */}
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <div className=" max-w-[600px]">
          {connectedSources.length > 0 ? (
            <div>
              {/* SECTION HEADER */}
              <div className="mb-2.5 flex items-center justify-between">
                <div className="text-[10px] font-medium text-zinc-500">
                  Connected sources
                </div>

                <div className="text-[9px] text-zinc-700">
                  {connectedSources.length}{" "}
                  {connectedSources.length === 1 ? "source" : "sources"}{" "}
                  connected
                </div>
              </div>

              {/* SOURCE LIST */}
              <div className="overflow-hidden rounded-lg border border-zinc-800/70 bg-[#111111]">
                {paginatedSources.map((source) => (
                  <SourceRow
                    key={source.id}
                    source={source}
                    onDisconnect={() => handleDisconnect(source.id)}
                    onReconnect={() => handleReconnect(source.id)}
                  />
                ))}
              </div>

              {/* PAGINATION */}
              {totalPages > 1 && (
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-[9px] text-zinc-700">
                    {getPaginationRange(currentPage, connectedSources.length)}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={goToPreviousPage}
                      disabled={currentPage === 1}
                      className="flex h-7 items-center gap-1 rounded-md border border-zinc-800 bg-[#111111] px-2.5 text-[9px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300 disabled:cursor-not-allowed disabled:text-zinc-800"
                    >
                      <ChevronLeft size={12} />

                      <span>Previous</span>
                    </button>

                    <div className="flex h-7 min-w-[72px] items-center justify-center rounded-md border border-zinc-800 bg-[#111111] px-2 text-[9px] text-zinc-600">
                      {currentPage} / {totalPages}
                    </div>

                    <button
                      type="button"
                      onClick={goToNextPage}
                      disabled={currentPage === totalPages}
                      className="flex h-7 items-center gap-1 rounded-md border border-zinc-800 bg-[#111111] px-2.5 text-[9px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300 disabled:cursor-not-allowed disabled:text-zinc-800"
                    >
                      <span>Next</span>

                      <ChevronRight size={12} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <EmptySources onConnect={() => setShowConnect(true)} />
          )}
        </div>
      </div>

      {/* CONNECT MODAL */}
      {showConnect && (
        <ConnectSourceModal
          isConnecting={isConnecting}
          onClose={() => {
            if (!isConnecting) {
              setShowConnect(false);
            }
          }}
          onConnect={handleConnectService}
        />
      )}
    </div>
  );
}

function SourceRow({
  source,
  onDisconnect,
  onReconnect,
}: {
  source: DocumentSource;
  onDisconnect: () => void;
  onReconnect: () => void;
}) {
  const sourceMeta = getSourceMeta(source);

  return (
    <div
      className={`group flex min-h-[64px] items-center gap-3 px-3.5 py-2.5 transition-colors hover:bg-white/[0.018] ${
        !source.connected ? "opacity-70" : ""
      }`}
    >
      {/* ICON */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${sourceMeta.iconBackground} ${sourceMeta.iconColor}`}
      >
        <sourceMeta.Icon size={15} strokeWidth={1.7} />
      </div>

      {/* NAME + TYPE */}
      <div className="min-w-0 flex-1">
        <div className="truncate text-[11px] font-medium text-zinc-200">
          {source.name}
        </div>

        <div className="mt-0.5 flex items-center gap-1.5 text-[9px] text-zinc-700">
          <span>{sourceMeta.label}</span>

          <span>·</span>

          <span>Added {source.createdAt}</span>
        </div>
      </div>

      {/* ACTION */}
      {source.connected ? (
        <button
          type="button"
          onClick={onDisconnect}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-zinc-700 transition-colors hover:bg-red-500/10 hover:text-red-400"
          title="Disconnect source"
        >
          <Trash2 size={12} />
        </button>
      ) : (
        <button
          type="button"
          onClick={onReconnect}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-zinc-700 transition-colors hover:bg-white/5 hover:text-zinc-300"
          title="Reconnect source"
        >
          <RefreshCw size={12} />
        </button>
      )}
    </div>
  );
}

function ConnectSourceModal({
  isConnecting,
  onClose,
  onConnect,
}: {
  isConnecting: boolean;
  onClose: () => void;
  onConnect: (option: ConnectOption) => void;
}) {
  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 px-4 backdrop-blur-[2px]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isConnecting) {
          onClose();
        }
      }}
    >
      <div className="w-full max-w-[430px] overflow-hidden rounded-lg border border-zinc-800/80 bg-[#151515] shadow-2xl">
        {/* HEADER */}
        <div className="flex items-center justify-between border-b border-zinc-800/70 px-4 py-3">
          <div>
            <h3 className="text-[13px] font-medium text-zinc-100">
              Connect a source
            </h3>

            <p className="mt-0.5 text-[10px] text-zinc-600">
              Choose where Tendo should get your information.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isConnecting}
            className="flex h-6 w-6 items-center justify-center rounded-md text-zinc-600 transition-colors hover:bg-white/5 hover:text-zinc-300 disabled:opacity-40"
          >
            <X size={14} />
          </button>
        </div>

        {/* OPTIONS */}
        <div className="space-y-1.5 p-3">
          <ConnectOptionRow
            icon={Folder}
            title="Computer folder"
            description="Use documents from a folder on your computer."
            onClick={() => onConnect("folder")}
            loading={isConnecting}
          />

          <ConnectOptionRow
            icon={MessageCircle}
            title="WhatsApp"
            description="Bring relevant conversations into Tendo."
            onClick={() => onConnect("whatsapp")}
            loading={isConnecting}
          />

          <ConnectOptionRow
            icon={Mail}
            title="Email"
            description="Connect your mailbox and learn from emails."
            onClick={() => onConnect("email")}
            loading={isConnecting}
          />

          <ConnectOptionRow
            icon={Video}
            title="Google Meet"
            description="Connect meeting information and conversations."
            onClick={() => onConnect("google-meet")}
            loading={isConnecting}
          />
        </div>

        {/* FOOTER */}
        <div className="border-t border-zinc-800/70 px-4 py-2.5">
          <div className="flex items-center gap-1.5 text-[8px] text-zinc-700">
            <Check size={10} />

            <span>
              Imported documents remain available after disconnecting a source.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConnectOptionRow({
  icon: Icon,
  title,
  description,
  onClick,
  loading = false,
}: {
  icon: typeof Folder;
  title: string;
  description: string;
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="group flex w-full items-center gap-2.5 rounded-lg border border-zinc-800/60 bg-[#111111] px-3 py-2.5 text-left transition-colors hover:border-zinc-700 hover:bg-[#131313] disabled:cursor-not-allowed disabled:opacity-50"
    >
      {/* ICON */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/[0.035] text-zinc-500">
        {loading ? (
          <RefreshCw size={14} className="animate-spin" />
        ) : (
          <Icon size={14} strokeWidth={1.7} />
        )}
      </div>

      {/* TEXT */}
      <div className="min-w-0 flex-1">
        <div className="text-[10px] font-medium text-zinc-200">{title}</div>

        <div className="mt-0.5 truncate text-[8px] text-zinc-700">
          {description}
        </div>
      </div>

      {/* ARROW */}
      {!loading && (
        <ChevronRightIcon
          size={12}
          className="shrink-0 text-zinc-800 transition-colors group-hover:text-zinc-500"
        />
      )}
    </button>
  );
}

function getSourceMeta(source: DocumentSource) {
  if (source.type === "folder") {
    return {
      Icon: Folder,
      label: "Computer folder",
      iconBackground: "bg-emerald-500/10",
      iconColor: "text-emerald-400",
    };
  }

  return {
    Icon: HardDrive,
    label: source.type,
    iconBackground: "bg-white/[0.035]",
    iconColor: "text-zinc-500",
  };
}

function getConnectOptionLabel(option: ConnectOption) {
  switch (option) {
    case "folder":
      return "computer folder";

    case "whatsapp":
      return "WhatsApp";

    case "email":
      return "Email";

    case "google-meet":
      return "Google Meet";

    default:
      return "source";
  }
}

function getPaginationRange(currentPage: number, totalSources: number) {
  const start = (currentPage - 1) * SOURCES_PER_PAGE + 1;

  const end = Math.min(currentPage * SOURCES_PER_PAGE, totalSources);

  return `${start}-${end} of ${totalSources} connected`;
}

function EmptySources({ onConnect }: { onConnect: () => void }) {
  return (
    <div className="flex min-h-[360px] flex-col items-center justify-center text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/[0.035] text-zinc-500">
        <Folder size={17} strokeWidth={1.6} />
      </div>

      <div className="mt-3 text-[12px] font-medium text-zinc-300">
        No sources connected
      </div>

      <div className="mt-1 max-w-[300px] text-[10px] leading-5 text-zinc-600">
        Connect a folder, WhatsApp, email or Google Meet so Tendo can find your
        information.
      </div>

      <button
        type="button"
        onClick={onConnect}
        className="mt-4 inline-flex h-8 items-center gap-1.5 rounded-md border border-zinc-800 bg-[#151515] px-3 text-[10px] font-medium text-zinc-400 transition-colors hover:border-zinc-700 hover:bg-[#191919] hover:text-zinc-200"
      >
        <Plus size={12} />
        Connect source
      </button>
    </div>
  );
}

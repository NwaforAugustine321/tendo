import { useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Link2,
  Loader2,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";

import type { DocumentFilter, KnowledgeDocument } from "../documents.types";

type Props = {
  documents: KnowledgeDocument[];
};

const FILTERS: {
  id: DocumentFilter;
  label: string;
}[] = [
  {
    id: "all",
    label: "All",
  },
  {
    id: "ready",
    label: "Ready",
  },
  {
    id: "processing",
    label: "Processing",
  },
  {
    id: "uploading",
    label: "Uploading",
  },
  {
    id: "failed",
    label: "Failed",
  },
];

const DOCUMENTS_PER_PAGE = 10;

const formatFileSize = (size: number) => {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  if (size < 1024 * 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(2)} MB`;
  }

  return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

const getStatusLabel = (status: KnowledgeDocument["status"]) => {
  switch (status) {
    case "ready":
      return "Ready";

    case "processing":
      return "Processing";

    case "uploading":
      return "Uploading";

    case "failed":
      return "Failed";

    default:
      return status;
  }
};

export default function DocumentsList({ documents }: Props) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<DocumentFilter>("all");

  const [currentPage, setCurrentPage] = useState(1);

  const filteredDocuments = useMemo(() => {
    const query = search.trim().toLowerCase();

    return documents.filter((document) => {
      const matchesSearch =
        !query ||
        document.name.toLowerCase().includes(query) ||
        document.type.toLowerCase().includes(query) ||
        document.entities.some(
          (entity: any) =>
            entity.name.toLowerCase().includes(query) ||
            entity.definitionName.toLowerCase().includes(query),
        );

      const matchesFilter = filter === "all" || document.status === filter;

      return matchesSearch && matchesFilter;
    });
  }, [documents, search, filter]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredDocuments.length / DOCUMENTS_PER_PAGE),
  );

  const paginatedDocuments = useMemo(() => {
    const startIndex = (currentPage - 1) * DOCUMENTS_PER_PAGE;

    const endIndex = startIndex + DOCUMENTS_PER_PAGE;

    return filteredDocuments.slice(startIndex, endIndex);
  }, [filteredDocuments, currentPage]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setCurrentPage(1);
  };

  const handleFilterChange = (value: DocumentFilter) => {
    setFilter(value);
    setCurrentPage(1);
  };

  const clearSearch = () => {
    setSearch("");
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setSearch("");
    setFilter("all");
    setCurrentPage(1);
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
        <div className="flex items-center justify-between gap-4 px-6 py-5">
          <div>
            <p className="mt-1 text-[11px] text-zinc-500">
              Documents Tendo has received and learned from.
            </p>
          </div>

          <div className="text-[11px] text-zinc-600">
            {filteredDocuments.length}{" "}
            {filteredDocuments.length === 1 ? "document" : "documents"}
          </div>
        </div>

        {/* SEARCH + FILTER */}
        <div className="flex items-center gap-2 px-6 pb-4">
          <div className="relative min-w-0 flex-1">
            <Search
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
            />

            <input
              type="text"
              value={search}
              onChange={(event) => handleSearchChange(event.target.value)}
              placeholder="Search documents or linked entities..."
              className="h-9 w-full rounded-lg border border-zinc-800 bg-[#111111] pl-9 pr-9 text-[11px] text-zinc-200 outline-none placeholder:text-zinc-700 focus:border-zinc-700"
            />

            {search && (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute right-2 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-zinc-600 hover:bg-white/5 hover:text-zinc-300"
              >
                <X size={12} />
              </button>
            )}
          </div>

          <div className="flex h-9 items-center gap-1 rounded-lg border border-zinc-800 bg-[#111111] px-1.5">
            <SlidersHorizontal size={12} className="mx-1.5 text-zinc-600" />

            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleFilterChange(item.id)}
                className={`rounded-md px-2.5 py-1.5 text-[10px] font-medium transition-colors ${
                  filter === item.id
                    ? "bg-white/[0.07] text-zinc-200"
                    : "text-zinc-600 hover:bg-white/[0.03] hover:text-zinc-400"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* DOCUMENT LIST */}
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
        {filteredDocuments.length > 0 ? (
          <div className="overflow-hidden rounded-l border border-zinc-800/70 bg-[#111111]">
            {/* LIST HEADER */}
            <div className="hidden grid-cols-[minmax(260px,1.8fr)_minmax(150px,1fr)_110px_120px] items-center gap-4 border-b border-zinc-800/60 bg-white/[0.015] px-4 py-2.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-zinc-700 md:grid">
              <span>Document</span>
              <span>Linked entity</span>
              <span>Source</span>
              <span>Status</span>
            </div>

            {/* ROWS */}
            <div className="divide-y divide-zinc-800/50">
              {paginatedDocuments.map((document) => (
                <DocumentRow key={document.id} document={document} />
              ))}
            </div>
          </div>
        ) : (
          <EmptyState
            hasSearch={Boolean(search.trim())}
            hasFilter={filter !== "all"}
            onClear={clearFilters}
          />
        )}
      </div>

      {/* PAGINATION */}
      {filteredDocuments.length > 0 && totalPages > 1 && (
        <div className="shrink-0 border-t border-zinc-800/70 px-6 py-3">
          <div className="flex items-center justify-between">
            {/* RANGE */}
            <div className="text-[10px] text-zinc-600">
              {getPaginationRange(currentPage, filteredDocuments.length)}
            </div>

            {/* CONTROLS */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={goToPreviousPage}
                disabled={currentPage === 1}
                className="flex h-8 items-center gap-1 rounded-md border border-zinc-800 bg-[#111111] px-2.5 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300 disabled:cursor-not-allowed disabled:border-zinc-800/60 disabled:text-zinc-800"
              >
                <ChevronLeft size={13} />

                <span>Previous</span>
              </button>

              <div className="flex h-8 min-w-[70px] items-center justify-center rounded-md border border-zinc-800 bg-[#111111] px-2 text-[10px] text-zinc-500">
                Page {currentPage} of {totalPages}
              </div>

              <button
                type="button"
                onClick={goToNextPage}
                disabled={currentPage === totalPages}
                className="flex h-8 items-center gap-1 rounded-md border border-zinc-800 bg-[#111111] px-2.5 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300 disabled:cursor-not-allowed disabled:border-zinc-800/60 disabled:text-zinc-800"
              >
                <span>Next</span>

                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getPaginationRange(currentPage: number, totalDocuments: number) {
  const start = (currentPage - 1) * DOCUMENTS_PER_PAGE + 1;

  const end = Math.min(currentPage * DOCUMENTS_PER_PAGE, totalDocuments);

  return `${start}-${end} of ${totalDocuments}`;
}

function DocumentRow({ document }: { document: KnowledgeDocument }) {
  const primaryEntity = document.entities[0];

  const remainingEntities = Math.max(document.entities.length - 1, 0);

  return (
    <div className="group px-4 py-3 transition-colors hover:bg-white/[0.018]">
      <div className="grid grid-cols-1 items-center gap-3 md:grid-cols-[minmax(260px,1.8fr)_minmax(150px,1fr)_110px_120px] md:gap-4">
        {/* DOCUMENT */}
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.035] text-zinc-500">
            <FileText size={15} strokeWidth={1.7} />
          </div>

          <div className="min-w-0">
            <div className="truncate text-[11px] font-medium text-zinc-200">
              {document.name}
            </div>

            <div className="mt-0.5 flex items-center gap-1.5 text-[9px] text-zinc-600">
              <span>{document.type}</span>

              <span>·</span>

              <span>{formatFileSize(document.size)}</span>

              <span>·</span>

              <span>{document.uploadedAt}</span>
            </div>
          </div>
        </div>

        {/* ENTITY */}
        <div className="min-w-0">
          {primaryEntity ? (
            <div className="flex min-w-0 items-center gap-1.5">
              <Link2 size={11} className="shrink-0 text-zinc-700" />

              <span className="truncate text-[10px] text-zinc-500">
                {primaryEntity.entryName}
              </span>

              {remainingEntities > 0 && (
                <span className="shrink-0 rounded-md bg-white/[0.035] px-1.5 py-0.5 text-[9px] text-zinc-600">
                  +{remainingEntities}
                </span>
              )}
            </div>
          ) : (
            <span className="text-[10px] text-zinc-700">No linked entity</span>
          )}
        </div>

        {/* SOURCE */}
        <div className="text-[10px] text-zinc-600">{document.source}</div>

        {/* STATUS */}
        <DocumentStatus status={document.status} />
      </div>
    </div>
  );
}

function DocumentStatus({ status }: { status: KnowledgeDocument["status"] }) {
  if (status === "ready") {
    return (
      <div className="flex items-center gap-1.5 text-[10px] text-emerald-400">
        <CheckCircle2 size={12} />

        <span>{getStatusLabel(status)}</span>
      </div>
    );
  }

  if (status === "processing") {
    return (
      <div className="flex items-center gap-1.5 text-[10px] text-amber-400">
        <Loader2 size={12} className="animate-spin" />

        <span>{getStatusLabel(status)}</span>
      </div>
    );
  }

  if (status === "uploading") {
    return (
      <div className="flex items-center gap-1.5 text-[10px] text-blue-400">
        <Loader2 size={12} className="animate-spin" />

        <span>{getStatusLabel(status)}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-[10px] text-red-400">
      <AlertCircle size={12} />

      <span>{getStatusLabel(status)}</span>
    </div>
  );
}

function EmptyState({
  hasSearch,
  hasFilter,
  onClear,
}: {
  hasSearch: boolean;
  hasFilter: boolean;
  onClear: () => void;
}) {
  const filtered = hasSearch || hasFilter;

  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white/[0.035] text-zinc-600">
        <FileText size={18} strokeWidth={1.6} />
      </div>

      <div className="mt-3 text-[13px] font-medium text-zinc-300">
        {filtered ? "No documents found" : "No documents yet"}
      </div>

      <div className="mt-1 max-w-[300px] text-[11px] leading-5 text-zinc-600">
        {filtered
          ? "Try a different search or filter."
          : "Documents you upload or connect will appear here."}
      </div>

      {filtered && (
        <button
          type="button"
          onClick={onClear}
          className="mt-4 rounded-md border border-zinc-800 bg-[#111111] px-3 py-2 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}

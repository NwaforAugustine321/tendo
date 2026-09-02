import { useEffect, useMemo, useState } from "react";
import { ChevronRight } from "lucide-react";

import type { KnowledgeItem } from "./knowledge.types";
import Pagination from "./Pagination";

const ITEMS_PER_PAGE = 5;

type Props = {
  items: KnowledgeItem[];
  onItemClick?: (item: KnowledgeItem) => void;
};

export default function KnowledgeList({ items, onItemClick }: Props) {
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(items.length / ITEMS_PER_PAGE));

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const paginatedItems = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;

    return items.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [items, currentPage]);

  const handlePrevious = () => {
    setCurrentPage((page) => Math.max(1, page - 1));
  };

  const handleNext = () => {
    setCurrentPage((page) => Math.min(totalPages, page + 1));
  };

  if (items.length === 0) {
    return (
      <div className="border-t border-zinc-800/60 py-10 text-center">
        <p className="text-[12px] text-zinc-500">Nothing found.</p>

        <p className="mt-1 text-[11px] text-zinc-700">
          Try a different search or filter.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="border-t border-zinc-800/60">
        {paginatedItems.map((item) => {
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onItemClick?.(item)}
              className="group flex w-full items-center border-b border-zinc-800/60 py-3.5 text-left transition-colors hover:bg-white/[0.018]"
            >
              <div className="flex min-w-0 flex-1 items-center gap-3 px-2">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/[0.035] text-zinc-500 transition-colors group-hover:bg-emerald-500/10 group-hover:text-emerald-400">
                  <Icon size={16} strokeWidth={1.7} />
                </div>

                <span className="truncate text-[13px] font-medium text-zinc-200">
                  {item.name}
                </span>
              </div>

              <div className="hidden w-[125px] text-right sm:block">
                <span className="text-[12px] text-zinc-500">
                  {item.records.toLocaleString()} records
                </span>
              </div>

              <div className="hidden w-[110px] text-right md:block">
                <span className="text-[11px] text-zinc-600">
                  {item.properties} properties
                </span>
              </div>

              <div className="flex w-10 justify-end pr-2">
                <ChevronRight
                  size={15}
                  strokeWidth={1.7}
                  className="text-zinc-700 transition-colors group-hover:text-zinc-400"
                />
              </div>
            </button>
          );
        })}
      </div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalItems={items.length}
        onPrevious={handlePrevious}
        onNext={handleNext}
      />
    </div>
  );
}

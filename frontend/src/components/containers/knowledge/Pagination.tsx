import { ChevronLeft, ChevronRight } from "lucide-react";

const ITEMS_PER_PAGE = 5;

type Props = {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  onPrevious: () => void;
  onNext: () => void;
};

export default function Pagination({
  currentPage,
  totalPages,
  totalItems,
  onPrevious,
  onNext,
}: Props) {
  const startItem =
    totalItems === 0 ? 0 : (currentPage - 1) * ITEMS_PER_PAGE + 1;

  const endItem = Math.min(currentPage * ITEMS_PER_PAGE, totalItems);

  return (
    <div className="flex items-center justify-between border-t border-zinc-800/40 py-3.5">
      <span className="text-[10px] text-zinc-600">
        {startItem}–{endItem} of {totalItems}
      </span>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={onPrevious}
          disabled={currentPage <= 1}
          className="flex h-7 items-center gap-1 rounded-md border border-zinc-800/70 bg-[#111111] px-2.5 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-25"
        >
          <ChevronLeft size={12} />
          Previous
        </button>

        <span className="min-w-[42px] text-center text-[10px] text-zinc-600">
          {currentPage} / {totalPages}
        </span>

        <button
          type="button"
          onClick={onNext}
          disabled={currentPage >= totalPages}
          className="flex h-7 items-center gap-1 rounded-md border border-zinc-800/70 bg-[#111111] px-2.5 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-25"
        >
          Next
          <ChevronRight size={12} />
        </button>
      </div>
    </div>
  );
}

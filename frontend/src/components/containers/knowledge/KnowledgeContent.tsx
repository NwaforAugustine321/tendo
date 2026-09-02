import { Search, Filter, ChevronDown, Check, RotateCcw } from "lucide-react";

import type { KnowledgeItem, KnowledgeSource } from "./knowledge.types";

import KnowledgeList from "./KnowledgeList";

type FilterItem = {
  id: string;
  name: string;
  count: number;
};

type SourceFilter = {
  id: KnowledgeSource;
  label: string;
  count: number;
};

type RecentFilter = {
  id: string;
  label: string;
  count: number;
};

type Props = {
  search: string;
  onSearchChange: (value: string) => void;

  knowledgeItems: KnowledgeItem[];
  filteredYourBusiness: KnowledgeItem[];
  filteredAddedByYou: KnowledgeItem[];

  selectedKnowledge: string[];
  selectedSource: KnowledgeSource[];
  selectedRecent: string[];

  appliedKnowledge: string[];
  appliedSource: KnowledgeSource[];
  appliedRecent: string[];

  expandedKnowledge: boolean;
  expandedSource: boolean;
  expandedRecent: boolean;

  knowledgeFilterItems: FilterItem[];
  sourceFilters: SourceFilter[];
  recentFilters: RecentFilter[];

  onToggleKnowledge: (id: string) => void;
  onToggleSource: (source: KnowledgeSource) => void;
  onToggleRecent: (id: string) => void;

  onToggleKnowledgeSection: () => void;
  onToggleSourceSection: () => void;
  onToggleRecentSection: () => void;

  onResetFilters: () => void;
  onApplyFilters: () => void;

  onAdd: () => void;
  onItemClick?: (item: KnowledgeItem) => void;
};

export default function KnowledgeContent({
  search,
  onSearchChange,
  knowledgeItems,
  filteredYourBusiness,
  filteredAddedByYou,
  selectedKnowledge,
  selectedSource,
  selectedRecent,
  appliedKnowledge,
  appliedSource,
  appliedRecent,
  expandedKnowledge,
  expandedSource,
  expandedRecent,
  knowledgeFilterItems,
  sourceFilters,
  recentFilters,
  onToggleKnowledge,
  onToggleSource,
  onToggleRecent,
  onToggleKnowledgeSection,
  onToggleSourceSection,
  onToggleRecentSection,
  onResetFilters,
  onApplyFilters,
  onAdd,
  onItemClick,
}: Props) {
  const hasPendingFilters =
    selectedKnowledge.length > 0 ||
    selectedSource.length > 0 ||
    selectedRecent.length > 0;

  const hasAppliedFilters =
    appliedKnowledge.length > 0 ||
    appliedSource.length > 0 ||
    appliedRecent.length > 0;

  return (
    <>
      {/* ================================================================ */}
      {/* FIXED FILTER PANEL                                               */}
      {/* ================================================================ */}

      <aside className="hidden w-[260px] shrink-0 lg:block">
        <div className="mt-[20px] flex h-[500px] flex-col border-x border-zinc-800/60 bg-[#151515]">
          {/* Header */}
          <div className="flex h-[64px] shrink-0 items-center justify-between border-b border-zinc-800/70 px-5">
            <div className="flex items-center gap-2.5">
              <Filter size={15} strokeWidth={1.8} className="text-zinc-400" />

              <span className="text-[13px] font-semibold text-zinc-100">
                Filters
              </span>
            </div>

            {hasAppliedFilters && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1.5 text-[9px] font-semibold text-black">
                {appliedKnowledge.length +
                  appliedSource.length +
                  appliedRecent.length}
              </span>
            )}
          </div>

          {/* Scrollable filter body */}
          <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-800">
            {/* ========================================================== */}
            {/* KNOWLEDGE                                                   */}
            {/* ========================================================== */}

            <section>
              <button
                type="button"
                onClick={onToggleKnowledgeSection}
                className="flex w-full items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
                  What Tendo Knows About
                </span>

                <ChevronDown
                  size={13}
                  className={`text-zinc-600 transition-transform ${
                    expandedKnowledge ? "" : "-rotate-90"
                  }`}
                />
              </button>

              {expandedKnowledge && (
                <div className="px-5 pb-4">
                  <div className="space-y-0.5">
                    {knowledgeFilterItems.map((item) => {
                      const checked = selectedKnowledge.includes(item.id);

                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => onToggleKnowledge(item.id)}
                          className="flex w-full items-center gap-2.5 rounded-md px-1 py-2 text-left transition-colors hover:bg-white/[0.025]"
                        >
                          <span
                            className={`flex h-[16px] w-[16px] shrink-0 items-center justify-center rounded-[4px] border ${
                              checked
                                ? "border-emerald-500 bg-emerald-500 text-black"
                                : "border-zinc-700"
                            }`}
                          >
                            {checked && <Check size={10} strokeWidth={2.5} />}
                          </span>

                          <span className="min-w-0 flex-1 truncate text-[12px] text-zinc-400">
                            {item.name}
                          </span>

                          <span className="text-[10px] text-zinc-600">
                            {item.count.toLocaleString()}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>

            <div className="border-t border-zinc-800/70" />

            {/* ========================================================== */}
            {/* SOURCE                                                       */}
            {/* ========================================================== */}

            <section>
              <button
                type="button"
                onClick={onToggleSourceSection}
                className="flex w-full items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
                  Source
                </span>

                <ChevronDown
                  size={13}
                  className={`text-zinc-600 transition-transform ${
                    expandedSource ? "" : "-rotate-90"
                  }`}
                />
              </button>

              {expandedSource && (
                <div className="px-5 pb-4">
                  <div className="space-y-0.5">
                    {sourceFilters.map((item) => {
                      const checked = selectedSource.includes(item.id);

                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => onToggleSource(item.id)}
                          className="flex w-full items-center gap-2.5 rounded-md px-1 py-2 text-left transition-colors hover:bg-white/[0.025]"
                        >
                          <span
                            className={`flex h-[16px] w-[16px] shrink-0 items-center justify-center rounded-[4px] border ${
                              checked
                                ? "border-emerald-500 bg-emerald-500 text-black"
                                : "border-zinc-700"
                            }`}
                          >
                            {checked && <Check size={10} strokeWidth={2.5} />}
                          </span>

                          <span className="min-w-0 flex-1 text-[12px] text-zinc-400">
                            {item.label}
                          </span>

                          <span className="text-[10px] text-zinc-600">
                            {item.count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>

            <div className="border-t border-zinc-800/70" />

            {/* ========================================================== */}
            {/* RECENTLY                                                     */}
            {/* ========================================================== */}

            <section>
              <button
                type="button"
                onClick={onToggleRecentSection}
                className="flex w-full items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
                  Recently
                </span>

                <ChevronDown
                  size={13}
                  className={`text-zinc-600 transition-transform ${
                    expandedRecent ? "" : "-rotate-90"
                  }`}
                />
              </button>

              {expandedRecent && (
                <div className="px-5 pb-4">
                  <div className="space-y-0.5">
                    {recentFilters.map((item) => {
                      const checked = selectedRecent.includes(item.id);

                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => onToggleRecent(item.id)}
                          className="flex w-full items-center gap-2.5 rounded-md px-1 py-2 text-left transition-colors hover:bg-white/[0.025]"
                        >
                          <span
                            className={`flex h-[16px] w-[16px] shrink-0 items-center justify-center rounded-[4px] border ${
                              checked
                                ? "border-emerald-500 bg-emerald-500 text-black"
                                : "border-zinc-700"
                            }`}
                          >
                            {checked && <Check size={10} strokeWidth={2.5} />}
                          </span>

                          <span className="min-w-0 flex-1 text-[12px] text-zinc-400">
                            {item.label}
                          </span>

                          <span className="text-[10px] text-zinc-600">
                            {item.count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>
          </div>

          {/* Footer */}
          <div className="flex h-[64px] shrink-0 items-center justify-between border-t border-zinc-800/70 bg-[#151515] px-4">
            <button
              type="button"
              onClick={onResetFilters}
              disabled={!hasPendingFilters && !hasAppliedFilters}
              className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] font-medium text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <RotateCcw size={12} />
              Reset
            </button>

            <button
              type="button"
              onClick={onApplyFilters}
              className="rounded-md bg-emerald-500 px-5 py-1.5 text-[11px] font-medium text-black transition-colors hover:bg-emerald-400"
            >
              Apply
            </button>
          </div>
        </div>
      </aside>

      {/* ================================================================ */}
      {/* MAIN CONTENT                                                      */}
      {/* ================================================================ */}

      <main className="min-w-0 flex-1 overflow-y-auto py-7 pr-2">
        <div className="mb-7">
          <h1 className="text-[20px] font-semibold tracking-[-0.01em] text-zinc-100">
            What Tendo Knows
          </h1>

          <p className="mt-1.5 text-[13px] text-zinc-500">
            Everything Tendo knows about your business.
          </p>
        </div>

        {/* Search */}
        <div className="mb-9 flex items-center gap-2">
          <div className="relative min-w-0 max-w-[520px] flex-1">
            <Search
              size={15}
              strokeWidth={1.8}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
            />

            <input
              type="text"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search knowledge..."
              className="h-9 w-full rounded-lg border border-zinc-800/70 bg-[#111111] pl-9 pr-3 text-[12px] text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-700"
            />
          </div>

          <button
            type="button"
            onClick={onAdd}
            className="flex h-9 shrink-0 items-center gap-1.5 rounded-lg bg-emerald-500 px-3 text-[12px] font-medium text-black transition-colors hover:bg-emerald-400"
          >
            <span>+</span>
            Add
          </button>
        </div>

        {/* ============================================================ */}
        {/* YOUR BUSINESS                                                 */}
        {/* ============================================================ */}

        <section className="mb-10">
          <div className="mb-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.11em] text-zinc-500">
              Your Business
            </h2>

            <p className="mt-1.5 text-[12px] text-zinc-600">
              The things Tendo understands about how your business works.
            </p>
          </div>

          <KnowledgeList
            items={filteredYourBusiness}
            onItemClick={onItemClick}
          />
        </section>

        {/* ============================================================ */}
        {/* ADDED BY YOU                                                  */}
        {/* ============================================================ */}

        <section>
          <div className="mb-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.11em] text-zinc-500">
              Added by You
            </h2>

            <p className="mt-1.5 text-[12px] text-zinc-600">
              Knowledge you've specifically taught Tendo.
            </p>
          </div>

          <KnowledgeList items={filteredAddedByYou} onItemClick={onItemClick} />
        </section>
      </main>
    </>
  );
}

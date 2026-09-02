import { ChevronLeft, MoreHorizontal, Pencil } from "lucide-react";

import type { KnowledgeDefinition, KnowledgeRecord } from "./knowledge.types";

type Props = {
  definition: KnowledgeDefinition;
  record: KnowledgeRecord;
  onBack: () => void;
  onEdit?: () => void;
};

function getFieldValue(
  definition: KnowledgeDefinition,
  record: KnowledgeRecord,
  fieldName: string,
) {
  const field = definition.fields.find(
    (item) => item.name.trim().toLowerCase() === fieldName.toLowerCase(),
  );

  return field ? record.values[field.id] : undefined;
}

function getDisplayName(
  definition: KnowledgeDefinition,
  record: KnowledgeRecord,
) {
  const name = getFieldValue(definition, record, "name");

  if (name?.trim()) {
    return name;
  }

  const firstValue = definition.fields
    .map((field) => record.values[field.id])
    .find((value) => value?.trim());

  return firstValue || "Untitled";
}

function getDescription(
  definition: KnowledgeDefinition,
  record: KnowledgeRecord,
) {
  return getFieldValue(definition, record, "description");
}

export default function KnowledgeDetail({
  definition,
  record,
  onBack,
  onEdit,
}: Props) {
  const displayName = getDisplayName(definition, record);
  const description = getDescription(definition, record);

  return (
    <div className="h-full min-h-0 overflow-y-auto">
      <div className="mx-auto w-full max-w-[900px] px-6 py-6">
        {/* Back */}
        <button
          type="button"
          onClick={onBack}
          className="group mb-7 flex items-center gap-1.5 text-[11px] text-zinc-600 transition-colors hover:text-zinc-300"
        >
          <ChevronLeft
            size={14}
            className="transition-transform group-hover:-translate-x-0.5"
          />
          {definition.name}
        </button>

        {/* Header */}
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <h1 className="text-[20px] font-medium tracking-[-0.01em] text-zinc-100">
              {displayName}
            </h1>

            {description && (
              <p className="mt-1.5 max-w-[650px] text-[12px] leading-5 text-zinc-500">
                {description}
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            {onEdit && (
              <button
                type="button"
                onClick={onEdit}
                className="flex h-8 items-center gap-1.5 rounded-md border border-zinc-800/70 bg-[#111111] px-3 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:text-zinc-300"
              >
                <Pencil size={12} />
                Edit
              </button>
            )}

            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-md border border-zinc-800/70 bg-[#111111] text-zinc-600 transition-colors hover:border-zinc-700 hover:text-zinc-300"
            >
              <MoreHorizontal size={14} />
            </button>
          </div>
        </div>

        {/* About */}
        <section className="mt-10">
          <SectionTitle>About</SectionTitle>

          <div className="mt-4 border-t border-zinc-800/60">
            {definition.fields.map((field) => {
              const value = record.values[field.id];

              if (!value?.trim()) {
                return null;
              }

              return (
                <div
                  key={field.id}
                  className="grid grid-cols-[180px_1fr] gap-6 border-b border-zinc-800/40 py-3.5"
                >
                  <span className="text-[11px] text-zinc-600">
                    {field.name}
                  </span>

                  <span className="text-[12px] leading-5 text-zinc-300">
                    {value}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* What Tendo Knows */}
        {record.understanding && record.understanding.length > 0 && (
          <section className="mt-10">
            <SectionTitle>What Tendo Knows</SectionTitle>

            <p className="mt-1.5 text-[11px] leading-5 text-zinc-600">
              Tendo has learned this from your conversations and business
              activity.
            </p>

            <div className="mt-4 space-y-2">
              {record.understanding.map((item, index) => (
                <div
                  key={`${item}-${index}`}
                  className="flex items-start gap-2.5 text-[12px] leading-5 text-zinc-400"
                >
                  <span className="mt-[8px] h-1 w-1 shrink-0 rounded-full bg-zinc-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Activity */}
        {record.activity && record.activity.length > 0 && (
          <section className="mt-10">
            <SectionTitle>Recent Activity</SectionTitle>

            <div className="mt-4 border-t border-zinc-800/60">
              {record.activity.map((activity) => (
                <div
                  key={activity.id}
                  className="flex gap-5 border-b border-zinc-800/40 py-3.5"
                >
                  <span className="w-[90px] shrink-0 text-[10px] text-zinc-600">
                    {activity.timestamp}
                  </span>

                  <div className="min-w-0">
                    <p className="text-[12px] text-zinc-300">
                      {activity.label}
                    </p>

                    {activity.description && (
                      <p className="mt-0.5 text-[11px] leading-5 text-zinc-600">
                        {activity.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Related */}
        {record.related && record.related.length > 0 && (
          <section className="mt-10 pb-10">
            <SectionTitle>Related</SectionTitle>

            <div className="mt-4 border-t border-zinc-800/60">
              {record.related.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="group flex w-full items-center border-b border-zinc-800/40 py-3.5 text-left transition-colors hover:bg-white/[0.018]"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12px] text-zinc-300">
                      {item.name}
                    </p>

                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="text-[10px] text-zinc-700">
                        {item.type}
                      </span>

                      {item.description && (
                        <>
                          <span className="text-zinc-800">·</span>
                          <span className="truncate text-[10px] text-zinc-600">
                            {item.description}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <ChevronLeft
                    size={14}
                    className="ml-4 rotate-180 text-zinc-700 transition-colors group-hover:text-zinc-400"
                  />
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">
      {children}
    </h2>
  );
}

import { useState } from "react";
import { ArrowLeft, X } from "lucide-react";

import type {
  KnowledgeDefinition,
  KnowledgeEntryValues,
} from "./knowledge.types";

type Props = {
  definition: KnowledgeDefinition;
  onBack: () => void;
  onClose: () => void;
  onSave: (values: KnowledgeEntryValues) => void | Promise<void>;
  isSaving?: boolean;
};

export default function KnowledgeEntryForm({
  definition,
  onBack,
  onClose,
  onSave,
  isSaving = false,
}: Props) {
  const [values, setValues] = useState<KnowledgeEntryValues>({});

  const updateValue = (fieldId: string, value: string) => {
    setValues((current) => ({
      ...current,
      [fieldId]: value,
    }));
  };

  const handleSave = async () => {
    if (isSaving) {
      return;
    }

    await onSave(values);
  };

  return (
    <div className="flex max-h-[620px] w-full max-w-[520px] flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-[#151515] shadow-2xl">
      {/* HEADER */}
      <div className="flex shrink-0 items-center gap-2 border-b border-zinc-800/70 px-5 py-4">
        <button
          type="button"
          onClick={onBack}
          disabled={isSaving}
          className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 hover:bg-white/5 hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ArrowLeft size={15} />
        </button>

        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-medium text-zinc-100">
            Add {definition.name}
          </h3>

          <p className="mt-1 text-[11px] text-zinc-500">
            Add the details Tendo should remember.
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
          disabled={isSaving}
          className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 hover:bg-white/5 hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <X size={15} />
        </button>
      </div>

      {/* BODY */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="space-y-5">
          {definition.fields.map((field) => (
            <div key={field.id}>
              <label className="mb-2 block text-[11px] font-medium text-zinc-300">
                {field.name}
              </label>

              <input
                type="text"
                value={values[field.id] ?? ""}
                onChange={(event) => updateValue(field.id, event.target.value)}
                disabled={isSaving}
                placeholder={`Enter ${field.name.toLowerCase()}`}
                className="h-10 w-full rounded-lg border border-zinc-800 bg-[#111111] px-3 text-[12px] text-zinc-200 outline-none placeholder:text-zinc-700 focus:border-emerald-500/50 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          ))}
        </div>
      </div>

      {/* FOOTER */}
      <div className="flex shrink-0 items-center justify-end gap-2 border-t border-zinc-800/70 px-5 py-3">
        <button
          type="button"
          onClick={onClose}
          disabled={isSaving}
          className="rounded-md px-3 py-2 text-[11px] font-medium text-zinc-500 hover:bg-white/5 hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Cancel
        </button>

        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="rounded-md bg-emerald-500 px-4 py-2 text-[11px] font-medium text-black hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isSaving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}

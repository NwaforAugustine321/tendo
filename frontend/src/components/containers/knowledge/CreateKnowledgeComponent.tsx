import { useState } from "react";
import { ArrowLeft, Plus, Trash2, X } from "lucide-react";

import type { KnowledgeDefinition, KnowledgeField } from "./knowledge.types";

type Props = {
  /**
   * When null/undefined:
   * create a completely new template.
   *
   * When provided:
   * edit the existing template.
   */
  definition?: KnowledgeDefinition | null;

  onBack: () => void;
  onClose: () => void;

  /**
   * Returns the newly created or edited definition.
   */
  onCreate: (definition: KnowledgeDefinition) => void;
};

const createDefaultFields = (): KnowledgeField[] => [
  {
    id: crypto.randomUUID(),
    name: "Name",
  },
  {
    id: crypto.randomUUID(),
    name: "Description",
  },
];

export default function CreateKnowledgeComponent({
  definition,
  onBack,
  onClose,
  onCreate,
}: Props) {
  const isEditing = Boolean(definition);

  /*
   * For a new template, start with an empty name/description
   * and useful default fields.
   *
   * For an existing template, load exactly what was previously
   * configured so editing does not destroy the current structure.
   */
  const [name, setName] = useState(definition?.name ?? "");

  const [description, setDescription] = useState(definition?.description ?? "");

  const [fields, setFields] = useState<KnowledgeField[]>(
    definition?.fields?.length
      ? definition.fields.map((field) => ({
          ...field,
        }))
      : createDefaultFields(),
  );

  const addField = () => {
    setFields((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        name: "",
      },
    ]);
  };

  const updateField = (id: string, value: string) => {
    setFields((current) =>
      current.map((field) =>
        field.id === id
          ? {
              ...field,
              name: value,
            }
          : field,
      ),
    );
  };

  const removeField = (id: string) => {
    setFields((current) => current.filter((field) => field.id !== id));
  };

  const handleSave = () => {
    const cleanName = name.trim();

    if (!cleanName) return;

    const cleanFields = fields
      .map((field) => ({
        ...field,
        name: field.name.trim(),
      }))
      .filter((field) => field.name);

    if (cleanFields.length === 0) return;

    /*
     * When editing, preserve the original definition ID.
     *
     * When creating, generate a new ID.
     */
    const definitionId =
      definition?.id ??
      `${cleanName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")}-${Date.now()}`;

    const updatedDefinition: KnowledgeDefinition = {
      id: definitionId,
      name: cleanName,
      description: description.trim(),
      fields: cleanFields,
    };

    onCreate(updatedDefinition);
  };

  const hasValidFields = fields.some((field) => field.name.trim().length > 0);

  return (
    <div className="flex max-h-[620px] w-full max-w-[520px] flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-[#151515] shadow-2xl">
      {/* =========================================================
          HEADER
          ========================================================= */}
      <div className="flex shrink-0 items-center gap-2 border-b border-zinc-800/70 px-5 py-4">
        <button
          type="button"
          onClick={onBack}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
        >
          <ArrowLeft size={15} />
        </button>

        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-medium text-zinc-100">
            {isEditing ? "Edit what Tendo knows" : "Add something new"}
          </h3>

          <p className="mt-1 text-[11px] text-zinc-500">
            {isEditing
              ? "Update what Tendo should know about each one."
              : "Teach Tendo about something specific."}
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
        >
          <X size={15} />
        </button>
      </div>

      {/* =========================================================
          BODY
          ========================================================= */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        {/* WHAT SHOULD TENDO KNOW */}
        <div>
          <label className="mb-2 block text-[11px] font-medium text-zinc-300">
            What should Tendo know?
          </label>

          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Suppliers"
            autoFocus
            className="h-10 w-full rounded-lg border border-zinc-800 bg-[#111111] px-3 text-[12px] text-zinc-200 outline-none placeholder:text-zinc-700 transition-colors focus:border-emerald-500/50"
          />
        </div>

        {/* ABOUT IT */}
        <div className="mt-5">
          <label className="mb-2 block text-[11px] font-medium text-zinc-300">
            About it
          </label>

          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Describe what this is and how it fits into your business."
            rows={3}
            className="w-full resize-none rounded-lg border border-zinc-800 bg-[#111111] px-3 py-2.5 text-[12px] leading-5 text-zinc-200 outline-none placeholder:text-zinc-700 transition-colors focus:border-emerald-500/50"
          />
        </div>

        {/* FIELDS */}
        <div className="mt-6">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div className="min-w-0">
              <label className="block text-[11px] font-medium text-zinc-300">
                What should Tendo know about each one?
              </label>

              <p className="mt-1 text-[10px] leading-4 text-zinc-600">
                These fields will appear whenever you add one.
              </p>
            </div>

            <button
              type="button"
              onClick={addField}
              className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1.5 text-[10px] font-medium text-emerald-400 transition-colors hover:bg-emerald-500/10"
            >
              <Plus size={12} />
              Add field
            </button>
          </div>

          <div className="space-y-2">
            {fields.map((field, index) => (
              <div key={field.id} className="flex items-center gap-2">
                {/* Field number */}
                <span className="flex h-9 w-5 shrink-0 items-center justify-center text-[9px] text-zinc-700">
                  {index + 1}
                </span>

                {/* Field name */}
                <input
                  type="text"
                  value={field.name}
                  onChange={(event) =>
                    updateField(field.id, event.target.value)
                  }
                  placeholder={`Field ${index + 1}`}
                  className="h-9 min-w-0 flex-1 rounded-lg border border-zinc-800 bg-[#111111] px-3 text-[11px] text-zinc-200 outline-none placeholder:text-zinc-700 transition-colors focus:border-emerald-500/50"
                />

                {/* Remove field */}
                <button
                  type="button"
                  onClick={() => removeField(field.id)}
                  disabled={fields.length <= 1}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-600 transition-colors hover:bg-white/5 hover:text-zinc-400 disabled:cursor-not-allowed disabled:opacity-30"
                  title="Remove field"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          {/* Empty field warning */}
          {!hasValidFields && (
            <p className="mt-2 text-[10px] text-amber-500/80">
              Add at least one field before continuing.
            </p>
          )}
        </div>
      </div>

      {/* =========================================================
          FOOTER
          ========================================================= */}
      <div className="flex shrink-0 items-center justify-end gap-2 border-t border-zinc-800/70 px-5 py-3">
        <button
          type="button"
          onClick={onClose}
          className="rounded-md px-3 py-2 text-[11px] font-medium text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
        >
          Cancel
        </button>

        <button
          type="button"
          onClick={handleSave}
          disabled={!name.trim() || !hasValidFields}
          className="rounded-md bg-emerald-500 px-4 py-2 text-[11px] font-medium text-black transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isEditing ? "Save changes" : "Create"}
        </button>
      </div>
    </div>
  );
}

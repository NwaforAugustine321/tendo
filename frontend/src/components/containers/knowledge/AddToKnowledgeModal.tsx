import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  FileText,
  Pencil,
  Plus,
  X,
} from "lucide-react";

import CreateKnowledgeComponent from "./CreateKnowledgeComponent";
import KnowledgeEntryForm from "./KnowledgeEntryForm";

import type {
  KnowledgeDefinition,
  KnowledgeEntryValues,
} from "./knowledge.types";

type Step = "choice" | "create" | "entry";

type Props = {
  definitions: KnowledgeDefinition[];

  onClose: () => void;

  /**
   * Called whenever a template is created or updated.
   *
   * The parent should add the definition if it is new,
   * or replace the existing definition if it was edited.
   */
  onDefinitionSaved: (definition: KnowledgeDefinition) => void;

  /**
   * Called when an entry is saved using a definition's
   * configured fields.
   */
  onSaveEntry: (
    definition: KnowledgeDefinition,
    values: KnowledgeEntryValues,
  ) => void;
};

const DEFINITIONS_PER_PAGE = 5;

export default function AddToKnowledgeModal({
  definitions,
  onClose,
  onDefinitionSaved,
  onSaveEntry,
}: Props) {
  const [step, setStep] = useState<Step>("choice");

  const [selectedDefinition, setSelectedDefinition] =
    useState<KnowledgeDefinition | null>(null);

  const [editingDefinition, setEditingDefinition] =
    useState<KnowledgeDefinition | null>(null);

  /*
   * Current page for the available templates.
   */
  const [definitionPage, setDefinitionPage] = useState(0);

  /*
   * -----------------------------------------------------------------------
   * PAGINATION
   * -----------------------------------------------------------------------
   */

  const totalDefinitionPages = Math.max(
    1,
    Math.ceil(definitions.length / DEFINITIONS_PER_PAGE),
  );

  const paginatedDefinitions = useMemo(() => {
    const start = definitionPage * DEFINITIONS_PER_PAGE;

    return definitions.slice(start, start + DEFINITIONS_PER_PAGE);
  }, [definitions, definitionPage]);

  const hasPreviousPage = definitionPage > 0;

  const hasNextPage = definitionPage < totalDefinitionPages - 1;

  const goToPreviousDefinitionPage = () => {
    setDefinitionPage((current) => Math.max(0, current - 1));
  };

  const goToNextDefinitionPage = () => {
    setDefinitionPage((current) =>
      Math.min(totalDefinitionPages - 1, current + 1),
    );
  };

  /*
   * If definitions change while the modal is open,
   * make sure the current page still exists.
   */
  useEffect(() => {
    setDefinitionPage((current) =>
      Math.min(current, Math.max(0, totalDefinitionPages - 1)),
    );
  }, [totalDefinitionPages]);

  /*
   * Keep the modal in a clean state when the component
   * is mounted.
   */
  useEffect(() => {
    setStep("choice");
    setSelectedDefinition(null);
    setEditingDefinition(null);
    setDefinitionPage(0);
  }, []);

  /*
   * -----------------------------------------------------------------------
   * CLOSE
   * -----------------------------------------------------------------------
   */

  const handleClose = () => {
    setStep("choice");
    setSelectedDefinition(null);
    setEditingDefinition(null);
    setDefinitionPage(0);

    onClose();
  };

  /*
   * -----------------------------------------------------------------------
   * SELECT TEMPLATE
   * -----------------------------------------------------------------------
   */

  const handleSelectDefinition = (definition: KnowledgeDefinition) => {
    setSelectedDefinition(definition);
    setEditingDefinition(null);
    setStep("entry");
  };

  /*
   * -----------------------------------------------------------------------
   * CREATE TEMPLATE
   * -----------------------------------------------------------------------
   */

  const handleStartCreate = () => {
    setEditingDefinition(null);
    setSelectedDefinition(null);
    setStep("create");
  };

  /*
   * -----------------------------------------------------------------------
   * EDIT TEMPLATE
   * -----------------------------------------------------------------------
   */

  const handleEditDefinition = (definition: KnowledgeDefinition) => {
    setEditingDefinition(definition);
    setSelectedDefinition(null);
    setStep("create");
  };

  /*
   * -----------------------------------------------------------------------
   * TEMPLATE SAVED
   * -----------------------------------------------------------------------
   */

  const handleDefinitionSaved = (definition: KnowledgeDefinition) => {
    onDefinitionSaved(definition);

    setSelectedDefinition(definition);
    setEditingDefinition(null);

    setStep("entry");
  };

  /*
   * -----------------------------------------------------------------------
   * ENTRY BACK
   * -----------------------------------------------------------------------
   */

  const handleEntryBack = () => {
    setSelectedDefinition(null);
    setStep("choice");
  };

  /*
   * -----------------------------------------------------------------------
   * CREATE BACK
   * -----------------------------------------------------------------------
   */

  const handleCreateBack = () => {
    setEditingDefinition(null);
    setStep("choice");
  };

  /*
   * -----------------------------------------------------------------------
   * RENDER
   * -----------------------------------------------------------------------
   */

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-[2px]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          handleClose();
        }
      }}
    >
      {/* =========================================================
          CHOOSE TEMPLATE
          ========================================================= */}
      {step === "choice" && (
        <div className="w-full max-w-[620px] overflow-hidden rounded-xl border border-zinc-800/80 bg-[#151515] shadow-2xl">
          {/* HEADER */}
          <div className="flex items-center justify-between border-b border-zinc-800/70 px-6 py-4">
            <div>
              <h3 className="text-[14px] font-medium text-zinc-100">
                Add to what I know
              </h3>

              <p className="mt-1 text-[11px] text-zinc-500">
                Choose what you want to add to Tendo.
              </p>
            </div>

            <button
              type="button"
              onClick={handleClose}
              className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300"
            >
              <X size={15} />
            </button>
          </div>

          {/* CONTENT */}
          <div className="p-5">
            {definitions.length > 0 ? (
              <>
                {/* EXISTING TEMPLATES */}
                <div>
                  <div className="mb-3 px-1">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
                      What Tendo can know
                    </div>

                    <div className="mt-1 text-[11px] text-zinc-600">
                      Choose something you've already set up.
                    </div>
                  </div>

                  {/* TEMPLATE LIST */}
                  <div className="space-y-1.5">
                    {paginatedDefinitions.map((definition) => (
                      <div
                        key={definition.id}
                        className="group flex items-center rounded-lg border border-zinc-800/70 bg-[#111111] transition-colors hover:border-zinc-700 hover:bg-[#131313]"
                      >
                        {/* MAIN SELECTION */}
                        <button
                          type="button"
                          onClick={() => handleSelectDefinition(definition)}
                          className="flex min-w-0 flex-1 items-center gap-3 p-3.5 text-left"
                        >
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400">
                            <FileText size={16} strokeWidth={1.7} />
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="truncate text-[12px] font-medium text-zinc-200">
                              {definition.name}
                            </div>

                            {definition.description ? (
                              <div className="mt-0.5 truncate text-[11px] text-zinc-600">
                                {definition.description}
                              </div>
                            ) : (
                              <div className="mt-0.5 text-[11px] text-zinc-600">
                                {definition.fields.length}{" "}
                                {definition.fields.length === 1
                                  ? "field"
                                  : "fields"}{" "}
                                configured
                              </div>
                            )}
                          </div>

                          <ChevronRight
                            size={14}
                            className="shrink-0 text-zinc-700 transition-colors group-hover:text-zinc-500"
                          />
                        </button>

                        {/* EDIT TEMPLATE */}
                        <button
                          type="button"
                          onClick={() => handleEditDefinition(definition)}
                          className="mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-600 transition-colors hover:bg-white/5 hover:text-zinc-300"
                          title="Edit template"
                        >
                          <Pencil size={13} strokeWidth={1.8} />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* PAGINATION */}
                  {totalDefinitionPages > 1 && (
                    <div className="mt-4 flex items-center justify-between border-t border-zinc-800/70 pt-3">
                      <div className="text-[10px] text-zinc-600">
                        {definitionPage * DEFINITIONS_PER_PAGE + 1}–
                        {Math.min(
                          (definitionPage + 1) * DEFINITIONS_PER_PAGE,
                          definitions.length,
                        )}{" "}
                        of {definitions.length}
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={goToPreviousDefinitionPage}
                          disabled={!hasPreviousPage}
                          className="flex h-7 items-center gap-1 rounded-md border border-zinc-800 bg-[#111111] px-2.5 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:bg-white/[0.025] hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <ChevronLeft size={12} />
                          Previous
                        </button>

                        <div className="flex h-7 min-w-7 items-center justify-center rounded-md bg-white/[0.04] px-2 text-[10px] font-medium text-zinc-400">
                          {definitionPage + 1}
                        </div>

                        <button
                          type="button"
                          onClick={goToNextDefinitionPage}
                          disabled={!hasNextPage}
                          className="flex h-7 items-center gap-1 rounded-md border border-zinc-800 bg-[#111111] px-2.5 text-[10px] font-medium text-zinc-500 transition-colors hover:border-zinc-700 hover:bg-white/[0.025] hover:text-zinc-300 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          Next
                          <ChevronRight size={12} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* CREATE ANOTHER */}
                <div className="mt-4 border-t border-zinc-800/70 pt-4">
                  <button
                    type="button"
                    onClick={handleStartCreate}
                    className="flex w-full items-center gap-3 rounded-lg border border-dashed border-zinc-800/80 bg-transparent p-3 text-left transition-colors hover:border-zinc-700 hover:bg-white/[0.02]"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400">
                      <Plus size={16} strokeWidth={1.8} />
                    </div>

                    <div className="min-w-0">
                      <div className="text-[12px] font-medium text-zinc-300">
                        Create something new
                      </div>

                      <div className="mt-0.5 text-[11px] text-zinc-600">
                        Define what Tendo should know and its fields.
                      </div>
                    </div>

                    <ChevronRight
                      size={14}
                      className="ml-auto shrink-0 text-zinc-700"
                    />
                  </button>
                </div>
              </>
            ) : (
              /* =====================================================
                 EMPTY STATE
                 ===================================================== */
              <div className="py-6">
                <div className="flex flex-col items-center text-center">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Plus size={19} strokeWidth={1.7} />
                  </div>

                  <div className="mt-3 text-[13px] font-medium text-zinc-200">
                    Nothing is set up yet
                  </div>

                  <div className="mt-1 max-w-[300px] text-[11px] leading-5 text-zinc-600">
                    Create a template first. You can choose the fields Tendo
                    should remember for each one.
                  </div>

                  <button
                    type="button"
                    onClick={handleStartCreate}
                    className="mt-4 inline-flex items-center gap-2 rounded-md bg-emerald-500 px-4 py-2 text-[11px] font-medium text-black transition-colors hover:bg-emerald-400"
                  >
                    <Plus size={13} />
                    Create a template
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================
          CREATE / EDIT TEMPLATE
          ========================================================= */}
      {step === "create" && (
        <CreateKnowledgeComponent
          definition={editingDefinition}
          onBack={handleCreateBack}
          onClose={handleClose}
          onCreate={handleDefinitionSaved}
        />
      )}

      {/* =========================================================
          ADD ENTRY
          ========================================================= */}
      {step === "entry" && selectedDefinition && (
        <KnowledgeEntryForm
          definition={selectedDefinition}
          onBack={handleEntryBack}
          onClose={handleClose}
          onSave={(values) => onSaveEntry(selectedDefinition, values)}
        />
      )}
    </div>
  );
}
